#!/bin/bash
start=`date +%s`

VIDEO=$1 #i.e. P02_14
SPARSE_PATH=$2 # path to save the sparse models
IMAGES_ROOT=$3 # root of epic kitchens images
SAMPLED_IMAGES=$4 # path of the sampeld images to be used for reconstruction
LOGS=$5 # to save the output logs
GPU_IDX=$6 # i.e. 0

PRE=$(echo "$VIDEO" | cut -d'_' -f1)
#cat $0 > "${LOGS}/$VIDEO.out"
mkdir ${SPARSE_PATH}/${VIDEO}
mkdir ${SPARSE_PATH}/${VIDEO}/sparse

colmap feature_extractor    \
    --database_path ${VIDEO}_database.db \
    --ImageReader.camera_model OPENCV \
    --image_list_path ${SAMPLED_IMAGES}/${VIDEO}_selected_frames.txt     \
    --ImageReader.single_camera 1     \
    --SiftExtraction.use_gpu 1 \
    --SiftExtraction.gpu_index $GPU_IDX \
    --image_path ${IMAGES_ROOT}/${PRE}/${VIDEO} \

colmap sequential_matcher \
     --database_path ${VIDEO}_database.db \
     --SiftMatching.use_gpu 1 \
     --SequentialMatching.loop_detection 1 \
     --SiftMatching.gpu_index $GPU_IDX \
     --SequentialMatching.vocab_tree_path vocab_bins/vocab_tree_flickr100K_words32K.bin \

colmap mapper     \
    --database_path ${VIDEO}_database.db     \
    --image_path ${PRE}/${VIDEO}     \
    --output_path ${SPARSE_PATH}/${VIDEO}/sparse \
    --image_list_path ${SAMPLED_IMAGES}/${VIDEO}_selected_frames.txt \


#echo "----------------------------------------------------------------------SUMMARY----------------------------------------------------------------------">> "${LOGS}/$VIDEO.out"
colmap model_analyzer --path ${SPARSE_PATH}/${VIDEO}/sparse/0/ > "${LOGS}/$VIDEO.out"

end=`date +%s`
runtime=$(((end-start)/60))
echo "$runtime minutes">> "${LOGS}/$VIDEO.out"
mv ${VIDEO}_database.db ${SPARSE_PATH}/${VIDEO}/database.db #move the database
