import pycolmap
import shutil
import os
import glob
import subprocess

def get_num_images(model_path):
    reconstruction = pycolmap.Reconstruction(model_path)
    num_images = reconstruction.num_images()
    return num_images

def read_lines_from_file(filename):
    """
    Read lines from a txt file and return them as a list.
    
    :param filename: Name of the file to read from.
    :return: List of lines from the file.
    """
    with open(filename, 'r') as file:
        lines = file.readlines()
    
    # Strip any trailing newline characters
    return [line.strip() for line in lines]

def keep_model_with_largest_images(reconstuction_path):
    all_models = sorted(glob.glob(os.path.join(reconstuction_path,'*')))
    try:
        max_images = get_num_images(all_models[0])
    except:
        return 0
    selected_model = all_models[0]
    if len(all_models) > 1:
        for model in all_models:
            num_images = get_num_images(model)
            if num_images > max_images:
                max_images = num_images
                selected_model = model

        for model in all_models:
            if model != selected_model:
                shutil.rmtree(model)   
        os.rename(selected_model,os.path.join(reconstuction_path,'0'))
    return max_images

    # Define the function to execute in each process
def run_script(script_path, arg):
    cmd = ['python3', script_path] + arg
    print(cmd)
    subprocess.call(cmd)