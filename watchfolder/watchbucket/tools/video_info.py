import subprocess
import json

FFPROBE_BIN = 'ffprobe4'

def get_video_info(video_file):
    FFPROBE_COMMAND = '%(ffprobe_bin)s -v quiet -print_format json -show_format -show_streams "%(video_file)s"' % \
                      dict(ffprobe_bin=FFPROBE_BIN, video_file=video_file)
    print FFPROBE_COMMAND
    proc = subprocess.Popen(FFPROBE_COMMAND, stdout=subprocess.PIPE, shell=True)
    (out, err) = proc.communicate()
    info = json.loads(out)
    return info

def get_video_stream_info(video_info):
    if not 'streams' in video_info:
        return None
    for stream in video_info['streams']:
        if stream['codec_type'] == 'video':
            return stream
    return None

def get_video_dimensions(video_uri):
    video_info = get_video_info(video_uri)
    video_stream = get_video_stream_info(video_info)
    return (int(video_stream['width']), int(video_stream['height']))