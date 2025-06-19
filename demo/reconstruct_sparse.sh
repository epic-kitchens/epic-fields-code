#!/bin/bash
start=`date +%s`

WORK_DIR=$1
CAMERA_MODEL=$2  # OPENCV or OPENCV_FISHEYE
GPU_IDX=0

IMGS_DIR=$WORK_DIR/frames
OUT_DIR=${WORK_DIR}/colmap

DB_PATH=${OUT_DIR}/database.db
SPARSE_DIR=${OUT_DIR}/sparse

mkdir -p ${OUT_DIR}
mkdir -p ${SPARSE_DIR}

#SIMPLE_PINHOLE
colmap feature_extractor    \
    --database_path ${DB_PATH} \
    --ImageReader.camera_model $CAMERA_MODEL \
    --image_list_path $WORK_DIR/homo90.txt     \
    --ImageReader.single_camera 1     \
    --SiftExtraction.use_gpu 1 \
    --SiftExtraction.gpu_index $GPU_IDX \
    --image_path $IMGS_DIR \

colmap sequential_matcher \
     --database_path ${DB_PATH} \
     --SiftMatching.use_gpu 1 \
     --SequentialMatching.loop_detection 1 \
     --SiftMatching.gpu_index $GPU_IDX \
     --SequentialMatching.vocab_tree_path vocab_bins/vocab_tree_flickr100K_words32K.bin \

colmap mapper     \
    --database_path ${DB_PATH}     \
    --image_path $IMGS_DIR    \
    --output_path ${SPARSE_DIR} \
    --image_list_path $WORK_DIR/homo90.txt \
    #--Mapper.ba_global_use_pba 1 \
    #--Mapper.ba_global_pba_gpu_index 0 1 \


end=`date +%s`

runtime=$(((end-start)/60))
echo "$runtime minutes"
