build:
	python setup.py build sdist bdist_wheel
upload:
	python setup.py upload sdist bdist_wheel