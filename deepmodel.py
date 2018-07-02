#coding:utf-8

import io
import pandas as pd
import numpy as np
from tqdm import tqdm #长循环进度条
from keras.models import Sequential, Model
from keras.layers import Dense, Activation, Dropout, Embedding, LSTM, GRU, Input, concatenate
from keras.layers.normalization import BatchNormalization
from keras.utils import np_utils
from keras.layers.merge import Concatenate
from keras.layers import TimeDistributed, Lambda, GlobalMaxPooling1D, Conv1D
from keras.callbacks import ModelCheckpoint
from keras import backend as K
from keras.layers.advanced_activations import PReLU
from keras.preprocessing import sequence, text
#import codec

print ("=====getting embedding matrix======")

def isnum(ch):
	print ch.isalnum()
	return ch.isalnum()

glove_path = './input/wiki.es.vec'
embeddings_index = {}
f = io.open(glove_path,encoding = 'utf8')
for line in f:
    values = line.split()
    word = values[0]
    coefs = np.asarray(values[1:], dtype='float32')
    embeddings_index[word] = coefs
f.close()



data = pd.read_csv(data_path,sep = ',',header = 0, low_memory = False)
data_test = pd.read_csv(data_test_path,sep = ',',header = 0, engine='python')

tk = text.Tokenizer(num_words=200000)
tk.fit_on_texts(list(data.question1.values) + list(data.question2.values.astype(str)) + list(data_test.question1.values) + list(data_test.question2.values.astype(str)))

word_index = tk.word_index
print("start to embedding len:%d"%len(word_index))
embedding_matrix = np.zeros((len(word_index) + 1, 300))
for word, i in tqdm(word_index.items()):
    embedding_vector = embeddings_index.get(word)
    if embedding_vector is not None:
        embedding_matrix[i] = embedding_vector


np.save(embedding_matrix_path,embedding_matrix)

#ytrain_enc = np_utils.to_categorical(y) #多分类编码

print('Build model...')

"""Input layers"""
feature1_input = Input(shape=(40,), dtype='int32', name='feature1_input')
feature2_input = Input(shape=(40,), dtype='int32', name='feature2_input')
feature3_input = Input(shape=(40,), dtype='int32', name='feature3_input')
feature4_input = Input(shape=(40,), dtype='int32', name='feature4_input')
feature5_input = Input(shape=(40,), dtype='int32', name='feature5_input')
feature6_input = Input(shape=(40,), dtype='int32', name='feature6_input')

#model 1
shared_embedding1 = Embedding(len(word_index) + 1,
                     300,
                     weights=[embedding_matrix],
                     input_length=40)
shared_timedis = TimeDistributed(Dense(300, activation='relu'))
shared_lamda = Lambda(lambda x: K.sum(x, axis=1), output_shape=(300,))

"""model 2"""
shared_embedding2 = Embedding(len(word_index) + 1,
                     300,
                     weights=[embedding_matrix],
                     input_length=40)

shared_conv1d_1 = Conv1D(padding="valid", 
                  activation="relu", 
                  filters=nb_filter, 
                  kernel_size=filter_length, 
                  strides=1)
shared_drop_1 = Dropout(0.2)
shared_conv1d_2 = Conv1D(padding="valid", 
                  activation="relu", 
                  filters=nb_filter, 
                  kernel_size=filter_length, 
                  strides=1)
shared_maxpool = GlobalMaxPooling1D()
shared_drop_2 = Dropout(0.2)
shared_dense = Dense(300)
shared_drop_3 = Dropout(0.2)
shared_batchnorm = BatchNormalization()





shared_embedding3 = Embedding(len(word_index) + 1,
                     300,
                     weights=[embedding_matrix],
                     input_length=40)
shared_lstm = LSTM(300, recurrent_dropout=0.2,dropout = 0.2)

#build
m1 = shared_embedding1(feature1_input)
m1 = shared_timedis(m1)
m1 = shared_lamda(m1)

m2 = shared_embedding1(feature2_input)
m2 = shared_timedis(m2)
m2 = shared_lamda(m2)

m3 = shared_embedding2(feature3_input)
m3 = shared_conv1d_1(m3)
m3 = shared_drop_1(m3)
m3 = shared_conv1d_2(m3)
m3 = shared_maxpool(m3)
m3 = shared_drop_2(m3)
m3 = shared_dense(m3)
m3 = shared_drop_3(m3)
m3 = shared_batchnorm(m3)

m4 = shared_embedding2(feature4_input)
m4 = shared_conv1d_1(m4)
m4 = shared_drop_1(m4)
m4 = shared_conv1d_2(m4)
m4 = shared_maxpool(m4)
m4 = shared_drop_2(m4)
m4 = shared_dense(m4)
m4 = shared_drop_3(m4)
m4 = shared_batchnorm(m4)

m5 = shared_embedding3(feature5_input)
m5 = shared_lstm(m5)

m6 = shared_embedding3(feature6_input)
m6 = shared_lstm(m6)


concat = concatenate([m1,m2,m3,m4,m5,m6])
x = Dense(300)(concat)
x = PReLU()(x)
x = Dropout(0.2)(x)
x = BatchNormalization()(x)

for i in range(3):
    x = Dense(300)(x)
    x = PReLU()(x)
    x = Dropout(0.2)(x)
    x = BatchNormalization()(x)

isduplicate = Dense(1, activation = 'sigmoid')(x)


merged_model = Model(input = [feature1_input,feature2_input,feature3_input,feature4_input,feature5_input,feature6_input], output = isduplicate)

merged_model.compile(loss='binary_crossentropy', optimizer='adam', metrics=['accuracy'])

checkpoint = ModelCheckpoint('weights.h5', monitor='val_acc', save_best_only=True, verbose=2)

merged_model.fit([x1, x2, x1, x2, x1, x2], y=y, batch_size=train_batch_size, epochs=train_epochs,
                 verbose=1, validation_split=0.1, shuffle=True, callbacks=[checkpoint])
print('saving sent2vec')
output_model = Model(input = [feature1_input,feature2_input,feature3_input,feature4_input,feature5_input,feature6_input], output = [m1,m2,m3,m4,m5,m6])
sent2vec = output_model.predict([x1, x2, x1, x2, x1, x2])
try:
    pd.DataFrame(sent2vec,columns=['x1_module1','x2_module1','x1_module2','x2_module2','x1_module3','x2_module3']).to_csv(sent_vector_path)
except ValueError:
    pd.DataFrame(sent2vec,index=['x1_module1','x2_module1','x1_module2','x2_module2','x1_module3','x2_module3']).to_csv(sent_vector_path)

print('start to predict')
predict = merged_model.predict([x1_test, x2_test, x1_test, x2_test, x1_test, x2_test])
pd.DataFrame(predict).to_csv(prediction_path)
