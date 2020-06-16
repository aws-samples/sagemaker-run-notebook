bucket=<bucket>
version=0.13.0
pkg=sagemaker_run_notebook-${version}.tar.gz
aws s3 cp s3://${bucket}/${pkg} /tmp
pip install /tmp/${pkg}
jlpm config set cache-folder /tmp/yarncache
jupyter lab build --debug --minimize=False
nohup supervisorctl -c /etc/supervisor/conf.d/supervisord.conf restart jupyterlabserver
