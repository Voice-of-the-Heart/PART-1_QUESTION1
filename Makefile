.PHONY: all clean install

all:
	bash run_pipeline.sh

install:
	pip install -r requirements.txt

clean:
	rm -rf output/*
