$PYTHON setup.py install --single-version-externally-managed --record=record.txt

mkdir -p $PREFIX/etc/conda/activate.d
mkdir -p $PREFIX/etc/conda/deactivate.d

ACTIVATE=$PREFIX/etc/conda/activate.d/happi
DEACTIVATE=$PREFIX/etc/conda/deactivate.d/happi

cp -f conda-recipe/activate.sh ${ACTIVATE}.sh
cp -f conda-recipe/deactivate.sh ${DEACTIVATE}.sh

unset ACTIVATE
unset DEACTIVATE
