# Basic conversion
python plex_converter.py input_video.mkv

# Specify output filename
python plex_converter.py input_video.mkv output_video.mp4

# High quality conversion with subtitles
python plex_converter.py -q 20 -s movie.mkv

# Batch convert all videos in current directory
python plex_converter.py -b

# Use faster preset for quicker conversion
python plex_converter.py -p faster video.mp4

# Very high quality batch conversion
python plex_converter.py -b -q 18 -p veryslow
