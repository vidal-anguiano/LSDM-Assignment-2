#!/bin/bash


apt-get update -y
apt install default-jre -y
apt install unzip -y

wget http://nlp.stanford.edu/software/stanford-corenlp-full-2018-10-05.zip
unzip stanford-corenlp-full-2018-10-05.zip
cd stanford-corenlp-full-2018-10-05
java -mx4g -cp "*" edu.stanford.nlp.pipeline.StanfordCoreNLPServer -port 9000 -timeout 15000
