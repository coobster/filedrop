from flask import Flask,g,send_file,abort,request,render_template
from werkzeug.utils import secure_filename
from sqlite3 import connect
from hashlib import sha256
from base64 import urlsafe_b64encode

from time import time,sleep
from io import BytesIO
from os.path import join
from threading import Thread

app = Flask(__name__)

DATABASE = 'filedrop_index.db'
#database loading function
def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = connect(DATABASE)
    return db

def hash_file(data):
  tmp_data = str(data).encode('utf-8')
  return sha256(tmp_data).digest()

def encode_url(data):
	return urlsafe_b64encode(data).decode()

def cleanup_robot():
	while True:
		db = connect(DATABASE)
		cur = db.cursor()
		# delete anything over 24 hours old
		results = cur.execute("SELECT url FROM links WHERE timestamp < ? AND url",(time()-86400,))
		for row in results.fetchall():
			cur.execute("UPDATE links SET data='',url='' WHERE url=?",(row[0],))
			print('Robot erased: {}'.format(row[0]))
		db.commit()
		db.close()
		sleep(1800) #run every 30 minutes

@app.route('/')
def index():
  return render_template('index.html')

@app.route('/upload',methods=["GET","POST"])
def upload():
	if request.method == 'POST':
		uploaded_file = request.files['file']
		data = uploaded_file.stream.read()
		data_hash = hash_file(data)
		filename = secure_filename(uploaded_file.filename)
		ext = filename.split('.')[-1]
		process_stamp = time()
		url = encode_url(hash_file(str(process_stamp)+str(data_hash)))

		if data != '':
			cur = get_db().cursor()
			cur.execute('INSERT INTO links VALUES(?,?,?,?,?,?,?)',(url,data_hash,data,process_stamp,ext,filename,request.remote_addr))
			get_db().commit()
			del cur
			return "{}{}".format(request.host_url,url)
		else:
			return abort(404)
	else:
		return abort(404)
@app.route('/<url>')
def get_file(url):
	cur = get_db().cursor()
	results = cur.execute("SELECT data,ext FROM links WHERE url=?",(url,))
	data = results.fetchone() 
	if data:
		cur.execute("UPDATE links SET url='',data='' WHERE url=?",(url,))
		get_db().commit()
		return send_file(BytesIO(data[0]),mimetype=data[1])
	else:
		return abort(404)

if __name__ == '__main__':
	bot = Thread(target=cleanup_robot,args=())
	bot.start()
	app.run(host='0.0.0.0',port=5000)
