#!/usr/bin/env python3

import os
import sys
import subprocess
import argparse
import glob
import shutil
from pathlib import Path

class PlexConverter:
    def __init__(self, quality=22, preset='slow', audio_bitrate='192k', copy_subtitles=False):
        self.quality = quality
        self.preset = preset
        self.audio_bitrate = audio_bitrate
        self.copy_subtitles = copy_subtitles
        self.video_extensions = ['.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.m4v']
        
    def check_ffmpeg(self):
        """Check if FFmpeg is installed"""
        try:
            subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
    
    def get_duration(self, file_path):
        """Get video duration in seconds"""
        cmd = [
            'ffprobe',
            '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            str(file_path)
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return float(result.stdout.strip())
        except (subprocess.CalledProcessError, ValueError):
            return None
    
    def convert_file(self, input_file, output_file=None):
        """Convert a single file to Plex-optimized format"""
        input_path = Path(input_file)
        
        if not input_path.exists():
            print(f"Error: File '{input_file}' does not exist.")
            return False
        
        if output_file is None:
            output_file = input_path.with_name(input_path.stem + '_plex.mp4')
        else:
            output_file = Path(output_file)
        
        # Check if output already exists
        if output_file.exists():
            overwrite = input(f"Output file '{output_file}' already exists. Overwrite? [y/N]: ")
            if overwrite.lower() != 'y':
                print("Skipping...")
                return False
        
        print(f"Converting: {input_path.name}")
        print(f"Output: {output_file}")
        print(f"Quality: CRF {self.quality}, Preset: {self.preset}")
        
        # Build FFmpeg command
        cmd = [
            'ffmpeg',
            '-i', str(input_path),
            '-c:v', 'libx264',
            '-preset', self.preset,
            '-crf', str(self.quality),
            '-c:a', 'aac',
            '-b:a', self.audio_bitrate,
            '-movflags', '+faststart',
            '-map_metadata', '0'
        ]
        
        if self.copy_subtitles:
            cmd.extend(['-c:s', 'mov_text'])
        
        cmd.append(str(output_file))
        
        try:
            # Get duration for progress indication
            duration = self.get_duration(input_path)
            
            # Start the conversion process
            process = subprocess.Popen(
                cmd,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )
            
            # Monitor progress
            for line in process.stderr:
                if duration and 'time=' in line:
                    # Extract time from FFmpeg output
                    time_str = line.split('time=')[1].split()[0]
                    try:
                        # Parse time (HH:MM:SS.ms format)
                        parts = time_str.split(':')
                        if len(parts) == 3:
                            hours, minutes, seconds = parts
                            current_time = int(hours) * 3600 + int(minutes) * 60 + float(seconds)
                            progress = (current_time / duration) * 100
                            print(f"\rProgress: {progress:.1f}%", end='', flush=True)
                    except (ValueError, IndexError):
                        pass
            
            process.wait()
            
            if process.returncode == 0:
                print("\n✓ Conversion completed successfully!")
                return True
            else:
                print("\n✗ Conversion failed!")
                return False
                
        except KeyboardInterrupt:
            print("\n\nConversion cancelled by user.")
            process.terminate()
            # Clean up partial output file
            if output_file.exists():
                output_file.unlink()
            return False
        except Exception as e:
            print(f"\nError during conversion: {e}")
            return False
    
    def batch_convert(self, directory='.'):
        """Convert all video files in a directory"""
        directory = Path(directory)
        video_files = []
        
        for ext in self.video_extensions:
            video_files.extend(directory.glob(f'*{ext}'))
        
        if not video_files:
            print(f"No video files found in {directory}")
            return
        
        print(f"Found {len(video_files)} video file(s) to convert:")
        for i, file in enumerate(video_files, 1):
            print(f"{i}. {file.name}")
        
        confirm = input("\nProceed with batch conversion? [y/N]: ")
        if confirm.lower() != 'y':
            print("Batch conversion cancelled.")
            return
        
        successful = 0
        failed = 0
        
        for i, file in enumerate(video_files, 1):
            print(f"\n[{i}/{len(video_files)}] Processing: {file.name}")
            if self.convert_file(file):
                successful += 1
            else:
                failed += 1
        
        print(f"\nBatch conversion complete!")
        print(f"Successful: {successful}")
        print(f"Failed: {failed}")

def main():
    parser = argparse.ArgumentParser(
        description='Convert videos to Plex-optimized format (H.264/AAC in MP4)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s video.mkv                    # Convert single file
  %(prog)s video.mkv output.mp4         # Convert with custom output name
  %(prog)s -q 20 -s video.mkv          # Higher quality with subtitles
  %(prog)s -b                          # Batch convert all videos in current directory
  %(prog)s -b -q 18 -p veryslow        # Batch convert with high quality
        """
    )
    
    parser.add_argument('input', nargs='?', help='Input video file')
    parser.add_argument('output', nargs='?', help='Output file (optional)')
    parser.add_argument('-b', '--batch', action='store_true', help='Batch convert all videos in current directory')
    parser.add_argument('-q', '--quality', type=int, default=22, choices=range(0, 52), metavar='CRF', help='CRF quality (0-51, lower=better, default: 22)')
    parser.add_argument('-p', '--preset', default='slow', choices=['ultrafast', 'superfast', 'veryfast', 'faster', 'fast', 'medium', 'slow', 'slower', 'veryslow'], help='x264 preset (default: slow)')
    parser.add_argument('-a', '--audio', type=int, default=192, help='Audio bitrate in kbps (default: 192)')
    parser.add_argument('-s', '--subtitles', action='store_true', help='Copy subtitles')
    
    args = parser.parse_args()
    
    converter = PlexConverter(
        quality=args.quality,
        preset=args.preset,
        audio_bitrate=f'{args.audio}k',
        copy_subtitles=args.subtitles
    )
    
    # Check if FFmpeg is installed
    if not converter.check_ffmpeg():
        print("Error: FFmpeg is not installed or not in PATH.")
        print("Please install FFmpeg first: https://ffmpeg.org/download.html")
        sys.exit(1)
    
    # Handle batch mode
    if args.batch:
        converter.batch_convert()
    elif args.input:
        # Convert single file
        converter.convert_file(args.input, args.output)
    else:
        parser.print_help()
        sys.exit(1)

if __name__ == '__main__':
    main()
