#!/bin/bash

rm -rf `find . -name __pycache__`

rm -rf `find . -name *.ipynb_checkpoints`

jupyter nbconvert --clear-output --inplace `find . -name *.ipynb`

