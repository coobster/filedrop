from flask import Flask,g,send_file,abort,request
from sqlite3 import connect
from hashlib import sha256
from time import time,sleep
from io import BytesIO
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
  return sha256(tmp_data).hexdigest()

def cleanup_robot():
	while True:
		db = connect(DATABASE)
		cur = db.cursor()
		# select files older than 24 hours
		results = cur.execute("SELECT url FROM links WHERE timestamp < ?",(time()-(86400),))
		for row in results.fetchall():
			cur.execute("DELETE FROM links WHERE url=?",(row[0],))
			print('Robot deleted: {}'.format(row[0]))
		db.commit()
		db.close()
		# run again in one hour
		sleep(3600)

@app.route('/')
def index():
  html = """

Upload your file and get a single use URL download for 24 hours:
<form action="/upload" method="POST" enctype="multipart/form-data">
<input type="file" name="file">
<br><input type="submit" value="Submit File">


"""
  return html

@app.route('/upload',methods=["GET","POST"])
def upload():
	if request.method == 'POST':
		uploaded_file = request.files['file']
		data = uploaded_file.stream.read()
		data_hash = hash_file(data)
		filename = secure_filename(uploaded_file.filename)
		ext = filename.split('.')[-1]
		process_stamp = time()
		url = hash_file(str(process_stamp)+str(data_hash))

		if data != '':
			cur = get_db().cursor()
			cur.execute('INSERT INTO links VALUES(?,?,?,?,?)',(url,data_hash,data,process_stamp,ext))
			get_db().commit()
			del cur
			return "{}".format(url)
		else:
			return "ERROR 403"
	else:
		return 'ERROR 404'
@app.route('/<filename>')
def get_file(filename):
	cur = get_db().cursor()
	results = cur.execute("SELECT data,ext FROM links WHERE url=?",(filename,))
	data = results.fetchone() 
	if data:
		cur.execute('DELETE FROM links WHERE url=?',(filename,))
		get_db().commit()
		return send_file(BytesIO(data[0]),mimetype=data[1])
	else:
		return "ERROR 404"

if __name__ == '__main__':
	# start the cleaning robot to remove files older than 24 hours
	bot = Thread(target=cleanup_robot,args=())
	bot.start()
	# start the flask app
	app.run(host='0.0.0.0',port=5000)
