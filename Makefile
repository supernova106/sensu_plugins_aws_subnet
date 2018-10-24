build:
	python3 setup.py build sdist bdist_wheel
upload:
	twine upload dist/*	