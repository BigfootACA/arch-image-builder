#!/usr/bin/env python3
import sys
import os

if __name__ == '__main__':
	sys.path.insert(0, os.path.realpath(os.path.dirname(__file__)))
	from builder.workflow import main
	main()
