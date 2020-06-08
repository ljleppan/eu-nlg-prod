#! /bin/bash
python -m cProfile -o run1.cprof eunlg/bulk_generate.py -o ../bulk_out/; pyprof2calltree -k -i run1.cprof
