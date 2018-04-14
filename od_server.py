#!/usr/bin/python3 -u

# Flask web server for object_detection using Tensorflow.   Receives a file path, sends back list of objects with scores

#HRESHOLD = .2
#THRESHOLD = .3
#THRESHOLD = .4
#THRESHOLD = .5
THRESHOLD = .7

COD_FILE    = '/home/bruce/bin/od_server.cod.save'
R_DIR       = '/home/bruce/workspace/tensorflow/models/research/'
IMAGES1_DIR = '/mnt/home/temp/is.o/'
IMAGES2_DIR = '/mnt/home/temp/is.b/'
NUM_CLASSES     = 90

# Point to utils and protos
import sys
sys.path.append(R_DIR)
sys.path.append(R_DIR + "object_detection")

# More models available from here: https://github.com/tensorflow/models/blob/master/research/object_detection/g3doc/detection_model_zoo.md
#MODEL_PATH = '/mnt/home/workspace/models/ssd_mobilenet_v1_coco_11_06_2017/frozen_inference_graph.pb'
MODEL_PATH = '/mnt/home/workspace/models/ssd_inception_v2_coco_2017_11_17/frozen_inference_graph.pb'
#MODEL_PATH = '/mnt/home/workspace/models/faster_rcnn_inception_v2_coco_2018_01_28/frozen_inference_graph.pb'
#MODEL_PATH = '/mnt/home/workspace/models/faster_rcnn_resnet50_coco_2018_01_28/frozen_inference_graph.pb'
#MODEL_PATH = '/mnt/home/workspace/models/faster_rcnn_resnet50_lowproposals_coco_2018_01_28/frozen_inference_graph.pb'
#MODEL_PATH = '/mnt/home/workspace/models/rfcn_resnet101_coco_2018_01_28/frozen_inference_graph.pb'
#MODEL_PATH = '/mnt/home/workspace/models/faster_rcnn_resnet101_coco_2018_01_28/frozen_inference_graph.pb'
#MODEL_PATH = '/mnt/home/workspace/models/faster_rcnn_resnet101_lowproposals_coco_2018_01_28/frozen_inference_graph.pb'
#MODEL_PATH = '/mnt/home/workspace/models/faster_rcnn_inception_resnet_v2_atrous_coco_2018_01_28/frozen_inference_graph.pb'
#MODEL_PATH = '/mnt/home/workspace/models/faster_rcnn_inception_resnet_v2_atrous_lowproposals_coco_2018_01_28/frozen_inference_graph.pb'
#MODEL_PATH = '/mnt/home/workspace/models/faster_rcnn_inception_resnet_v2_atrous_coco_2018_01_28/frozen_inference_graph.pb'
#MODEL_PATH = '/mnt/home/workspace/models/faster_rcnn_nas_coco_2018_01_28/frozen_inference_graph.pb'
#MODEL_PATH = '/mnt/home/workspace/models/mask_rcnn_inception_v2_coco_2018_01_28/frozen_inference_graph.pb'
#MODEL_PATH = '/mnt/home/workspace/models/mask_rcnn_resnet101_atrous_coco_2018_01_28/frozen_inference_graph.pb'
#MODEL_PATH = '/mnt/home/workspace/models/mask_rcnn_resnet50_atrous_coco_2018_01_28/frozen_inference_graph.pb'
#MODEL_PATH = '/home/bruce/workspace/ncsdk/examples/tensorflow/inception_v3/graph'

#http://localhost:8009/?file_dir=/mnt/home/temp/is1/&file=C2%20411-20180305-0828467168.jpg
#
# On nuc without gpu
#Execution time:    758.27 ssd_mobilenet_v1_coco_11_06_2017                        [{'name': 'bear', 'score': '0.712996'}]
#Execution time:    930.54 ssd_inception_v2_coco_2017_11_17                        [{'score': '0.712996', 'name': 'bear'}]
#Execution time:   2778.72 faster_rcnn_inception_v2_coco_2018_01_28                [{'score': '0.995324', 'name': 'dog'}]
#Execution time:   7251.75 faster_rcnn_resnet50_coco_2018_01_28                    [{'score': '0.881098', 'name': 'dog'}, {'score': '0.633622', 'name': 'bear'}]
#Execution time:   4554.20 faster_rcnn_resnet50_lowproposals_coco_2018_01_28       [{'score': '0.881098', 'name': 'dog'}, {'score': '0.633621', 'name': 'bear'}]
#Execution time:   9330.14 rfcn_resnet101_coco_2018_01_28                          [{'score': '0.990999', 'name': 'dog'}, {'score': '0.760146', 'name': 'bear'}]
#Execution time:  10034.49 faster_rcnn_resnet101_coco_2018_01_28                   [{'score': '0.985908', 'name': 'dog'}]
#Execution time:   7620.29 faster_rcnn_resnet101_lowproposals_coco_2018_01_28      [{'score': '0.985908', 'name': 'dog'}]
#Execution time:  59534.11 faster_rcnn_inception_resnet_v2_atrous_coco_2018_01_28  [{'score': '0.967845', 'name': 'dog'}]
#Execution time:  33644.32 faster_rcnn_inception_resnet_v2_atrous_lowproposals_coco_2018_01_28  [{'score': '0.967845', 'name': 'dog'}]
#Execution time: 152382.79 faster_rcnn_nas_coco_2018_01_28                         [{'name': 'dog', 'score': '0.997074'}, {'name': 'bear', 'score': '0.976385'}]
#Execution time:   6419.02 mask_rcnn_inception_v2_coco_2018_01_28                  [{'score': '0.944098', 'name': 'dog'}, {'score': '0.930818', 'name': 'bear'}]
#Execution time:  69755.12 mask_rcnn_resnet101_atrous_coco_2018_01_28              [{'name': 'dog', 'score': '0.948599'}, {'name': 'bird', 'score': '0.633946'}]
#Execution time:  28147.10 mask_rcnn_resnet50_atrous_coco_2018_01_28               [{'score': '0.954802', 'name': 'dog'}]

# On nucw with gpu
#Execution time:    133.27 ssd_mobilenet_v1_coco_11_06_2017                        []
#Execution time:    262.54 ssd_inception_v2_coco_2017_11_17                        [{'score': '0.712996', 'name': 'bear'}]
#Execution time:    256.72 faster_rcnn_inception_v2_coco_2018_01_28                [{'score': '0.995324', 'name': 'dog'}]
#Execution time:    279.75 faster_rcnn_resnet50_coco_2018_01_28                    [{'score': '0.861098', 'name': 'dog'}, {'score': '0.413622', 'name': 'bear'}]
#Execution time:   xxxx    faster_rcnn_resnet50_lowproposals_coco_2018_01_28       [{'score': '0.881098', 'name': 'dog'}, {'score': '0.633621', 'name': 'bear'}]
#Execution time:    278.14 rfcn_resnet101_coco_2018_01_28                          [{'score': '0.990999', 'name': 'dog'}, {'score': '0.820146', 'name': 'bear'}]
#Execution time:    311.49 faster_rcnn_resnet101_coco_2018_01_28                   [{'score': '0.985908', 'name': 'dog'}]
#Execution time:    265.29 faster_rcnn_resnet101_lowproposals_coco_2018_01_28      [{'score': '0.985908', 'name': 'dog'}]
#Execution time:    938.11 faster_rcnn_inception_resnet_v2_atrous_coco_2018_01_28  [{'score': '0.967845', 'name': 'dog'}]
#Execution time:    529.26 faster_rcnn_inception_resnet_v2_atrous_lowproposals_coco_2018_01_28  [{'score': '0.967845', 'name': 'dog'}]
#Execution time:   1816.79 faster_rcnn_nas_coco_2018_01_28                         [{'name': 'dog', 'score': '0.997074'}, {'name': 'bear', 'score': '0.976385'}]
#Execution time:    130.02 mask_rcnn_inception_v2_coco_2018_01_28                  [{'score': '0.964098', 'name': 'dog'}, {'score': '0.920818', 'name': 'bear'}]
#Execution time:    634.12 mask_rcnn_resnet101_atrous_coco_2018_01_28              [{'name': 'dog', 'score': '0.948599'}, {'name': 'bird', 'score': '0.633946'}]
#Execution time:    418.10 mask_rcnn_resnet50_atrous_coco_2018_01_28               [{'score': '0.914802', 'name': 'dog'}]


import collections
import cv2
import numpy as np
import os
import pickle
import tensorflow as tf
import time
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from flask import Flask, jsonify, request
from shutil import copyfile
from utils import label_map_util
from utils import visualization_utils as vis_util
from PIL   import Image

app = Flask(__name__)
app.config.from_object(__name__)

# Read Count Objects Detected data, so we can ignore false objects that do not move
#od = collections.defaultdict(dict)
cod = collections.defaultdict(int)
if os.path.isfile(COD_FILE): 
    print(time.ctime() + " Loading " + COD_FILE)
    cod = pickle.load(open(COD_FILE, "rb" ) )

# Read the graph definition file
print(time.ctime() + " Loading model=" + MODEL_PATH)
with open(MODEL_PATH, 'rb') as f:
    graph_def = tf.GraphDef()
    graph_def.ParseFromString(f.read())

# Load the graph stored in `graph_def` into `graph`
detection_graph = tf.Graph() 
with detection_graph.as_default():
    tf.import_graph_def(graph_def, name='')
    
# Enforce that no new nodes are added
detection_graph.finalize()

# Create the session that we'll use to execute the model
sess_config = tf.ConfigProto(
    log_device_placement=False,
    allow_soft_placement = True,
    gpu_options = tf.GPUOptions(
        per_process_gpu_memory_fraction=1
    )
)
sess = tf.Session(graph=detection_graph, config=sess_config)

label_map = label_map_util.load_labelmap(R_DIR + 'object_detection/data/mscoco_label_map.pbtxt')
categories = label_map_util.convert_label_map_to_categories(label_map, max_num_classes=NUM_CLASSES, use_display_name=True)
category_index = label_map_util.create_category_index(categories)

print(time.ctime() + " Graph loaded")

def load_image_into_numpy_array(image):
    (im_width, im_height) = image.size
    return np.array(image.getdata()).reshape(
        (im_height, im_width, 3)).astype(np.uint8)

@app.route('/')
def classify():

    t = time.time()

    file_dir  = request.args['file_dir']
    file      = request.args['file']
    file_path = file_dir + "/" + file
    camera    = file[0:2]

#   print(time.ctime() + " Classifying image %s" % (file_path),)

    image = Image.open(file_path)

# Note: load_image on 4k images is 10+ seconds!   So have ss limit snapshot filesize, since we resize small for object detection anyway
    image_np = load_image_into_numpy_array(image)
#   image_np = cv2.resize(image_np, (1280,720))

#   print(time.ctime() + " Load time: %0.2f" % ((time.time() - t) * 1000.))

    image_np_expanded = np.expand_dims(image_np, axis=0)
    image_tensor   = detection_graph.get_tensor_by_name('image_tensor:0')
    boxes          = detection_graph.get_tensor_by_name('detection_boxes:0')
    scores         = detection_graph.get_tensor_by_name('detection_scores:0')
    classes        = detection_graph.get_tensor_by_name('detection_classes:0')
    num_detections = detection_graph.get_tensor_by_name('num_detections:0')

    (boxes, scores, classes, num_detections) = sess.run([boxes, scores, classes, num_detections], feed_dict={image_tensor: image_np_expanded})

    objects = []
    for index, value in enumerate(classes[0]):
#       print("i=" + str(index) + " v=" + str(value))
        object_dict = {}
        if scores[0, index] > THRESHOLD:
            cat = (category_index.get(value)).get('name')
            score = str(scores[0, index])
            object_dict = {"name"  : cat, "score" : score}

            # Update a Count-Object-Detected (cod) counter so we can learn to ignore repeated objects.
            # This assumes if the same object (type, box size, and box position) is recognized frequently, then
            # it is probably a fixed, uninteresting object, like a shadow that looks like a person.
            bb1 = boxes[0, index]
            i = camera + " " + cat + " " + str([ '%.1f' % i for i in bb1 ])
            cod[i] += 1
            if(cod[i] < 10):
                objects.append(object_dict)
                print(time.ctime() + " Score: " + score + " Object kepted:  i=" + i + " c=" + str(cod[i]))
            else:
                print(time.ctime() + " Score: " + score + " Object ignored: i=" + i + " c=" + str(cod[i]))
    print(time.ctime() + " Execution time: %0.2f. " % ((time.time() - t) * 1000.) + str(objects))
     
    if(len(objects) > 0):
        vis_util.visualize_boxes_and_labels_on_image_array(
            image_np,
            np.squeeze(boxes),
            np.squeeze(classes).astype(np.int32),
            np.squeeze(scores),
            category_index,
            use_normalized_coordinates=True,
            min_score_thresh=THRESHOLD,
            line_thickness=8)
        cat = objects[0]['name']
        file = cat + '_' + file
        file_path_out1 = IMAGES1_DIR + file
        file_path_out2 = IMAGES2_DIR + file
        copyfile(file_path, file_path_out1)
        cv2.imwrite( file_path_out2, cv2.resize(image_np, (1280,720)) );
        
# Note: objects needs strings, not integer, scores to avoid this error:  to avoid TypeError: is not JSON serializable
    return jsonify(objects)
#   return json.dumps(objects)
#   return jsonify(scores.tolist())
   
def cod_save():
    print(time.ctime() + " Saving " + COD_FILE)
    pickle.dump( cod, open( COD_FILE, "wb" ) )

# Clear counters for infrequently flagged objects, so we don't accidently ignore non-static objects that happened to be in the same place    
def cod_adjust():
    print(time.ctime() + " Adjusting cod")
#   for i in cod:
    for i in list(cod):
        cod[i] -= 1
        if cod[i] < 1:
            del cod[i]

if __name__ == '__main__':

    scheduler = BackgroundScheduler()
    scheduler.start()
    scheduler.add_job(cod_save,   'cron', hour='*')
#   scheduler.add_job(cod_save,   'cron', minute='*/15')
    scheduler.add_job(cod_adjust, 'cron', day='*')
    
    app.run(debug=False, port=8009)
#   app.run(debug=True, port=8009)
#   app.run(debug=True, host='192.168.86.150', port=8009)

    
