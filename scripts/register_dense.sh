start=`date +%s`

VIDEO=$1 #i.e. P02_14
SPARSE_PATH=$2 # path to save the sparse models
DENSE_PATH=$3 # path to save the sparse models
IMAGES_ROOT=$4 # root of epic kitchens images
LOGS=$5 # to save the output logs
GPU_IDX=$6 # i.e. 0

PRE=$(echo "$VIDEO" | cut -d'_' -f1)

cp ${SPARSE_PATH}/${VIDEO}/database.db ${VIDEO}_database.db #move the database from the sparse model
mkdir ${DENSE_PATH}/${VIDEO}

colmap feature_extractor    \
    --database_path ${VIDEO}_database.db \
    --ImageReader.camera_model OPENCV \
    --ImageReader.single_camera 1     \
    --ImageReader.existing_camera_id 1 \
    --SiftExtraction.use_gpu 1 \
    --SiftExtraction.gpu_index $GPU_IDX \
    --image_path ${IMAGES_ROOT}/${PRE}/${VIDEO} \



colmap sequential_matcher \
     --database_path ${VIDEO}_database.db \
     --SiftMatching.use_gpu 1 \
     --SequentialMatching.loop_detection 1 \
     --SiftMatching.gpu_index $GPU_IDX \
     --SequentialMatching.vocab_tree_path vocab_bins/vocab_tree_flickr100K_words32K.bin \


colmap image_registrator    \
     --database_path ${VIDEO}_database.db \
     --input_path ${SPARSE_PATH}/${VIDEO}/sparse/0    \
     --output_path ${DENSE_PATH}/${VIDEO} \


colmap model_analyzer --path ${DENSE_PATH}/${VIDEO} > "${LOGS}/$VIDEO.out"

end_reg=`date +%s`

runtime=$(((end_reg-start)/60))
echo "$runtime minutes (registration time)">> "${LOGS}/$VIDEO.out"

rm ${VIDEO}_database.db #remove the database since it's too large, you can keep it upon your usecase
