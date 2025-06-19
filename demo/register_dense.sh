#!/bin/bash
start=`date +%s`

GPU_IDX=0

WORK_DIR=$1
CAMERA_MODEL=$2
MAX_SPARSE_IND=$3
IMGS_DIR=$WORK_DIR/frames
OUT_DIR=${WORK_DIR}/colmap

DB_PATH=${OUT_DIR}/database.db
SPARSE_DIR=${OUT_DIR}/sparse

REG_DIR=${OUT_DIR}/registered
mkdir -p $REG_DIR

VIDEOUID=`basename $WORK_DIR`
REG_DB_PATH=${OUT_DIR}/reg${VIDEOUID}.db
echo $VIDOEUID $REG_DB_PATH
rm -f $REG_DB_PATH $REG_DB_PATH-shm $REG_DB_PATH-wal
cp $DB_PATH $REG_DB_PATH

colmap feature_extractor    \
    --database_path ${REG_DB_PATH} \
    --ImageReader.camera_model $CAMERA_MODEL \
    --ImageReader.single_camera 1     \
    --ImageReader.existing_camera_id 1 \
    --SiftExtraction.use_gpu 1 \
    --SiftExtraction.gpu_index $GPU_IDX \
    --image_path $IMGS_DIR

colmap sequential_matcher \
     --database_path ${REG_DB_PATH} \
     --SiftMatching.use_gpu 1 \
     --SequentialMatching.loop_detection 1 \
     --SiftMatching.gpu_index $GPU_IDX \
     --SequentialMatching.vocab_tree_path vocab_bins/vocab_tree_flickr100K_words32K.bin \

colmap image_registrator    \
     --database_path $REG_DB_PATH \
     --input_path $SPARSE_DIR/$MAX_SPARSE_IND    \
     --output_path $REG_DIR \

# Release space after successful registration
if [ -e $REG_DIR/images.bin ]; then
     rm -f $REG_DB_PATH $REG_DB_PATH-shm $REG_DB_PATH-wal
fi

end_reg=`date +%s`

runtime=$(((end_reg-start)/60))
echo "$runtime minutes"

