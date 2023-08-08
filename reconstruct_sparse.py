import subprocess
import shutil
import os
import time
import glob
import argparse
import pycolmap
from utils.lib import *
# Function to parse command-line arguments
def parse_args():
    parser = argparse.ArgumentParser(description='COLMAP Reconstruction Script')
    parser.add_argument('--input_videos', type=str, default='input_videos.txt',
                        help='A file with list of vidoes to be processed in all stages')
    parser.add_argument('--sparse_reconstuctions_root', type=str, default='colmap_models/sparse',
                        help='Path to the sparsely reconstructed models.')
    parser.add_argument('--epic_kithens_root', type=str, default='.',
                        help='Path to epic kitchens images.')
    parser.add_argument('--logs_path', type=str, default='logs/sparse/out_logs_terminal',
                        help='Path to store the log files.')
    parser.add_argument('--summary_path', type=str, default='logs/sparse/out_summary',
                        help='Path to store the summary files.')
    parser.add_argument('--sampled_images_path', type=str, default='sampled_frames',
                        help='Path to the directory containing sampled image files.')
    parser.add_argument('--gpu_index', type=int, default=0,
                        help='Index of the GPU to use.')

    return parser.parse_args()


args = parse_args()

gpu_index = args.gpu_index

videos_list = read_lines_from_file(args.input_videos)
videos_list = sorted(videos_list)
print('GPU: %d' % (gpu_index))
os.makedirs(args.logs_path, exist_ok=True)
os.makedirs(args.summary_path, exist_ok=True)
os.makedirs(args.sparse_reconstuctions_root, exist_ok=True)

i = 0
for video in videos_list:
    pre = video.split('_')[0]
    if (not os.path.exists(os.path.join(args.sparse_reconstuctions_root, '%s' % video))):
        # check the number of images in this video
        with open(os.path.join(args.sampled_images_path, '%s_selected_frames.txt' % (video)), 'r') as f:
            lines = f.readlines()
            num_lines = len(lines)
        #print(f'The file {video} contains {num_lines} lines.')
        if num_lines < 100000: #it's too large, so it would take days! 
            print('Processing: ', video, '(',num_lines, 'images )')
            start_time = time.time()

            # Define the path to the shell script
            script_path = 'scripts/reconstruct_sparse.sh'

            # Create a unique copy of the script
            script_copy_path = video + '_' + str(os.getpid()) + '_' + os.path.basename(script_path)
            shutil.copy(script_path, script_copy_path)

            # Output file
            output_file_path = os.path.join(args.logs_path, script_copy_path.replace('.sh', '.out'))


            # Define the command to execute the script
            command = ["bash", script_copy_path, video,args.sparse_reconstuctions_root,args.epic_kithens_root,args.sampled_images_path,args.summary_path,str(gpu_index)]
            # Open the output file in write mode
            with open(output_file_path, 'w') as output_file:
                # Run the command and capture its output in real time
                process = subprocess.Popen(command, stdout=output_file, stderr=subprocess.PIPE, text=True)
                while True:
                    output = process.stderr.readline()
                    if output == '' and process.poll() is not None:
                        break
                    if output:
                        output_file.write(output)
                        output_file.flush()

            # Once the script has finished running, you can delete the copy of the script
            os.remove(script_copy_path)

            #In case of having multiple models, will keep the one with largest number of images and rename it as 0
            reg_images = keep_model_with_largest_images(os.path.join(args.sparse_reconstuctions_root,video,'sparse'))
            if reg_images > 0:
                print(f"Registered_images/total_images: {reg_images}/{num_lines} = {round(reg_images/num_lines*100)}%")
            else:
                print('The video reconstruction fails!! no reconstruction file is found!')




            print("Execution time:  %s minutes" % round((time.time() - start_time)/60, 0))
            print('-----------------------------------------------------------')

    i += 1

