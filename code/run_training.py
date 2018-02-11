from data_provider import ASSISTDataProvider
from LstmModel import LstmModel

from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter
from time import gmtime, strftime

import os
import numpy as np
import tensorflow as tf

import matplotlib
matplotlib.use('agg')
import matplotlib.pyplot as plt

START_TIME = strftime('%Y%m%d-%H%M', gmtime())

parser = ArgumentParser(description='Train LstmModel.',
                        formatter_class=ArgumentDefaultsHelpFormatter)
parser.add_argument('--data_dir', type=str,
                    default='~/Dropbox/mlp-group-project/',
                    help='Path to directory containing data')
parser.add_argument('--restore', default=None,
                    help='Path to .ckpt file of model to continue training')
parser.add_argument('--learn_rate',  type=float, default=0.01,
                    help='Initial learning rate for Adam optimiser')
parser.add_argument('--batch',  type=int, default=100,
                    help='Batch size')
parser.add_argument('--epochs', type=int, default=20,
                    help='Number of training epochs')
parser.add_argument('--decay', type=float, default=0.98,
                    help='Fraction to decay learning rate every 100 batches')
parser.add_argument('--name', type=str, default=START_TIME,
                    help='Name of experiment when saving model')
parser.add_argument('--model_dir', type=str, default='.',
                    help='Path to directory where model will be saved')
args = parser.parse_args()

Model = LstmModel()
TrainingSet = ASSISTDataProvider(args.data_dir, batch_size=args.batch)

print('Experiment started at', START_TIME)
print("Building model...")
Model.build_graph(n_hidden_units=200, learning_rate=args.learn_rate,
                  decay_exp=args.decay)

save_dir = args.model_dir+'/'+args.name
os.mkdir(save_dir)

print("Model built!")

train_saver = tf.train.Saver()
with tf.Session() as sess:
    merged = tf.summary.merge_all()
    train_writer = tf.summary.FileWriter(save_dir+'/train', sess.graph)
    sess.run(tf.global_variables_initializer())
    sess.run(tf.local_variables_initializer())  # required for metrics

    if args.restore:
        train_saver.restore(sess, tf.train.latest_checkpoint(args.restore))
        print("Model restored!")

    print("Starting training...")
    for epoch in range(args.epochs):
        for i, (inputs, targets, target_ids) in enumerate(TrainingSet):
            # Train!
            _, loss, (accuracy, _), (auc, _), summary = sess.run(
                [Model.training, Model.loss, Model.accuracy, Model.auc, merged],
                feed_dict={Model.inputs: inputs,
                           Model.targets: targets,
                           Model.target_ids: target_ids})
        
        train_writer.add_summary(summary, epoch)
        print("Epoch: {},  Loss: {:.3f},  Accuracy: {:.3f},  AUC: {:.3f}"
              .format(epoch, loss, accuracy, auc))

        # save model each epoch
        save_path = "{}/{}_{}.ckpt".format(save_dir, args.name, epoch)
        train_saver.save(sess, save_path)
    print("Saved model at", save_path)

    #Save figure of loss, accuracy, auc graph
    event_dir = train_writer.get_logdir()
    event_file = ""
    
    for (path, names, files) in os.walk(event_dir):
        event_file = event_dir+'/'+files[0]
        break
    
    print(event_file)
    result = []

    for e in tf.train.summary_iterator(event_file):
        value_set =[]
        is_result = False
        for v in e.summary.value:
            if v.tag=='loss' or v.tag=='accuracy_1' or v.tag=='auc_1':
                value_set.append(v.simple_value)
                is_result = True
                
        if is_result:
            result.append(value_set)
    
    result = np.array(result)
    print(result)
    e = np.arange(0.0,args.epochs, 1.0)
    plt.plot(e, result[:,0])
    plt.xlabel('epoch')
    plt.ylabel('loss')
    plt.title('Loss per epoch')
    plt.savefig(save_dir+'/train/loss.png')
    
    plt.plot(e, result[:,1])
    plt.xlabel('epoch')
    plt.ylabel('accuracy')
    plt.title('Accuracy per epoch')
    plt.savefig(save_dir+'/train/accuracy.png')
    
    plt.plot(e, result[:,2])
    plt.xlabel('epoch')
    plt.ylabel('auc')
    plt.title('AUC per epoch')
    plt.savefig(save_dir+'/train/auc.png')
    
