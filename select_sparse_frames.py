import subprocess
import concurrent.futures
import glob
import os
import argparse
from utils.lib import *
# Function to parse command-line arguments
def parse_args():
    parser = argparse.ArgumentParser(description='COLMAP Reconstruction Script')
    parser.add_argument('--input_videos', type=str, default='input_videos.txt',
                        help='A file with list of vidoes to be processed in all stages')
    parser.add_argument('--epic_kithens_root', type=str, default='.',
                        help='Path to epic kitchens images.')
    parser.add_argument('--sampled_images_path', type=str, default='sampled_frames',
                        help='Path to the directory containing sampled image files.')
    parser.add_argument('--homography_overlap', type=float, default=0.9,
                        help='Threshold of the homography to sample new frames, higher value samples more images')
    parser.add_argument('--max_concurrent', type=int, default=8,
                        help='Max number of concurrent processes')
    return parser.parse_args()




def main():
    args = parse_args()

    videos = read_lines_from_file(args.input_videos)
    epic_root = args.epic_kithens_root
    params_list = []
    for video in videos:
        video_pre = video.split('_')[0]
        for folder in sorted(glob.glob(os.path.join(epic_root,video_pre+'/*'))):
            video = folder.split('/')[-1] 
            if video in videos:
                print(video)
                added_run = ['--src', folder, '--dst_file', '%s/%s_selected_frames.txt'%(args.sampled_images_path,video), '--overlap', str(args.homography_overlap)]
                if not added_run  in params_list:
                                params_list.append(added_run)
                    
    if params_list:
        max_concurrent = args.max_concurrent
        # Create a process pool executor with a maximum of K processes
        executor = concurrent.futures.ProcessPoolExecutor(max_workers=max_concurrent)

        # Submit the tasks to the executor
        results = []
        for i in range(len(params_list)):
            future = executor.submit(run_script, 'homography_filter/filter.py', params_list[i % len(params_list)])
            results.append(future)

        # Wait for all tasks to complete
        for r in concurrent.futures.as_completed(results):
            try:
                r.result()
            except Exception as e:
                print(f"Error occurred: {e}")

        # Shut down the executor
        executor.shutdown()


if __name__ == '__main__':
    main()