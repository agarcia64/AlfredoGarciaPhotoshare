######################################
# author ben lawson <balawson@bu.edu> 
# Edited by: Craig Einstein <einstein@bu.edu>
######################################
# Some code adapted from 
# CodeHandBook at http://codehandbook.org/python-web-application-development-using-flask-and-mysql/
# and MaxCountryMan at https://github.com/maxcountryman/flask-login/
# and Flask Offical Tutorial at  http://flask.pocoo.org/docs/0.10/patterns/fileuploads/
# see links for further understanding
###################################################

import flask
from flask import Flask, Response, request, render_template, redirect, url_for
from flaskext.mysql import MySQL
#import flask.ext.login as flask_login
import flask_login
#for image uploading
from werkzeug import secure_filename
import os, base64
import random
import re

mysql = MySQL()
app = Flask(__name__)
app.secret_key = 'super secret string'  # Change this!

#These will need to be changed according to your creditionals
app.config['MYSQL_DATABASE_USER'] = 'root'
app.config['MYSQL_DATABASE_PASSWORD'] = 'H2F3jk67er' #CHANGE THIS TO YOUR MYSQL PASSWORD
app.config['MYSQL_DATABASE_DB'] = 'photoshare'
app.config['MYSQL_DATABASE_HOST'] = 'localhost'
mysql.init_app(app)

#begin code used for login
login_manager = flask_login.LoginManager()
login_manager.init_app(app)

conn = mysql.connect()
cursor = conn.cursor()
cursor.execute("SELECT email from Users") 
users = cursor.fetchall()

def getUserList():
	cursor = conn.cursor()
	cursor.execute("SELECT email from Users") 
	return cursor.fetchall()

class User(flask_login.UserMixin):
	pass

@login_manager.user_loader
def user_loader(email):
	users = getUserList()
	if not(email) or email not in str(users):
		return
	user = User()
	user.id = email
	return user

@login_manager.request_loader
def request_loader(request):
	users = getUserList()
	email = request.form.get('email')
	if not(email) or email not in str(users):
		return
	user = User()
	user.id = email
	cursor = mysql.connect().cursor()
	cursor.execute("SELECT password FROM Users WHERE email = '{0}'".format(email))
	data = cursor.fetchall()
	pwd = str(data[0][0] )
	user.is_authenticated = request.form['password'] == pwd
	return user


'''
A new page looks like this:
@app.route('new_page_name')
def new_page_function():
	return new_page_html
'''

@app.route('/login', methods=['GET', 'POST'])
def login():
	if flask.request.method == 'GET':
		return '''
			   <form action='login' method='POST'>
				<input type='text' name='email' id='email' placeholder='email'></input>
				<input type='password' name='password' id='password' placeholder='password'></input>
				<input type='submit' name='submit'></input>
			   </form></br>
		   <a href='/'>Home</a>
			   '''
	#The request method is POST (page is recieving data)
	email = flask.request.form['email']
	cursor = conn.cursor()
	#check if email is registered
	if cursor.execute("SELECT password FROM Users WHERE email = '{0}'".format(email)):
		data = cursor.fetchall()
		pwd = str(data[0][0] )
		if flask.request.form['password'] == pwd:
			user = User()
			user.id = email
			flask_login.login_user(user) #okay login in user
			return flask.redirect(flask.url_for('protected')) #protected is a function defined in this file

	#information did not match
	return "<a href='/login'>Try again</a>\
			</br><a href='/register'>or make an account</a>"

@app.route('/logout')
def logout():
	flask_login.logout_user()
	return render_template('hello.html', message='Logged out') 

@login_manager.unauthorized_handler
def unauthorized_handler():
	return render_template('unauth.html') 

#you can specify specific methods (GET/POST) in function header instead of inside the functions as seen earlier
@app.route("/register/", methods=['GET'])
def register():
	return render_template('improved_register.html', supress='True')  

@app.route("/register/", methods=['POST'])
def register_user():
	try:
		email    = request.form.get('email')
		password = request.form.get('password')
		dob      = request.form.get('birthday')
		hometown = request.form.get('hometown')
		gender   = request.form.get('gender')
		first    = request.form.get('firstname')
		last     = request.form.get('lastname')
		try: 
			bio      = request.form.get('bio')
			proPic   = request.form.get('photo')
		except:
			bio = ""
			proPic = open("\static\default.png","r")
			proPic = base64.standard_b64encode(proPic.read())
	except:
		print("couldn't find all tokens")
		return flask.redirect(flask.url_for('register'))


	cursor = conn.cursor()
	test =  isEmailUnique(email)
	if test:
		tempUserId = int(random.uniform(1,999999))

		# Check if user_id is unique
		cursor.execute("SELECT user_id FROM Users WHERE user_id='{0}'".format(tempUserId))
		tempCheckId = cursor.fetchall()
		while (tempUserId == tempCheckId):
			cursor.execute("SELECT user_id FROM Users WHERE user_id='{0}'".format(tempUserId))
			tempCheckId = cursor.fetchall()

		print(cursor.execute("INSERT INTO Users (user_id, email, password, bio, dob, hometown, gender, first, last, profilePic) \
			VALUES ('{0}', '{1}', '{2}', '{3}','{4}','{5}','{6}','{7}','{8}', '{9}')".format(tempUserId,email,password,bio,dob,hometown,gender,first,last,proPic)))
		conn.commit()
		#log user in
		user = User()
		user.id = email
		flask_login.login_user(user)
		return render_template('hello.html', name=email, message='Account Created!')
	else:
		print("couldn't find all tokens")
		return flask.redirect(flask.url_for('register'))

def getUsersPhotos(uid):
	cursor = conn.cursor()
	cursor.execute("SELECT imgdata, picture_id, caption FROM Pictures WHERE user_id = '{0}'".format(uid))
	return cursor.fetchall() #NOTE list of tuples, [(imgdata, pid), ...]

def getUserIdFromEmail(email):
	cursor = conn.cursor()
	cursor.execute("SELECT user_id  FROM Users WHERE email = '{0}'".format(email))
	return cursor.fetchone()[0]

def isEmailUnique(email):
	#use this to check if a email has already been registered
	cursor = conn.cursor()
	if cursor.execute("SELECT email  FROM Users WHERE email = '{0}'".format(email)): 
		#this means there are greater than zero entries with that email
		return False
	else:
		return True
#end login code

@app.route('/profile')
@flask_login.login_required
def protected():
	return render_template('hello.html', name=flask_login.current_user.id, message="Here's your profile")

#begin photo uploading code
# photos uploaded using base64 encoding so they can be directly embeded in HTML 
ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg', 'gif'])
def allowed_file(filename):
	return '.' in filename and filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS

@app.route('/upload', methods=['GET', 'POST'])
@flask_login.login_required
def upload_file():
	if request.method == 'POST':
		uid           = getUserIdFromEmail(flask_login.current_user.id)
		imgfile       = request.files['photo']
		caption       = request.form.get('caption')
		tag           = request.form.get('tag')
		photo_data    = base64.standard_b64encode(imgfile.read())
		tempPictureId = int(random.uniform(1,999999))
		tempAlbumId   = request.form.get("albumId")

		cursor = conn.cursor()
		
		# Check if picture_id is unique
		cursor.execute("SELECT picture_id FROM Pictures WHERE picture_id='{0}'".format(tempPictureId))
		tempCheckId = cursor.fetchall()
		while (tempPictureId == tempCheckId):
			cursor.execute("SELECT picture_id FROM Pictures WHERE picture_id='{0}'".format(tempPictureId))
			tempCheckId = cursor.fetchall()

		# Get the album name
		cursor.execute("SELECT name FROM Albums WHERE albumId = '{0}'".format(tempAlbumId))
		tempAlbumName = str(cursor.fetchall())
		tempAlbumName = re.sub('[(),]','',tempAlbumName)
		
		# Check if the tag exists
		cursor.execute("SELECT * FROM Tags WHERE tag = '{0}'".format(tag))
		tempTag = str(cursor.fetchall())
		tempTag = re.sub('[(),\']','',tempTag)

		if (str(tag) != tempTag):
			cursor.execute("INSERT INTO Tags VALUES ('{0}')".format(tag))
			conn.commit()
		else:
			print("Already exists")

		# Insert the picture
		cursor.execute("INSERT INTO Pictures (picture_id, albumId, user_id, imgdata, caption) VALUES (%s,%s,%s,%s,%s)",(tempPictureId,tempAlbumId,uid,photo_data, caption))
		conn.commit()

		# Associate the tag with the picture
		cursor.execute("INSERT INTO PictureHasTag (picture_id, tag, albumId) VALUES ('{0}','{1}','{2}')".format(tempPictureId, tag, tempAlbumId))
		conn.commit()

		# Get the pictures to display
		cursor.execute("SELECT * FROM Pictures WHERE user_id='{0}' AND albumId='{1}'".format(uid,tempAlbumId))
		tempListPhotos = pictureIntoFormat(list(cursor.fetchall()))

		return render_template('pictures.html', name=tempAlbumName, photoList=tempListPhotos, album=tempAlbumId)
	#The method is GET so we return a  HTML form to upload the a photo.
	else:
		return render_template('upload.html')
#end photo uploading code 

###################################################################
# Functions for albums                                            #
###################################################################
@app.route('/albums')
@flask_login.login_required
def albums():
	print("albums()")
	tempUserAlbums = getAllAlbumsFromUser()
	return render_template('albums.html', albumList=tempUserAlbums)

@app.route('/createAlbum', methods=['GET', 'POST'])
def createAlbum():
	# Grab user info
	tempUserName   = request.form.get('name')
	tempUserId     = getUserIdFromEmail(flask_login.current_user.id)
	tempUserAlbums = getAllAlbumsFromUser()
	tempAlbumId    = int(random.uniform(1,999999))
	
	cursor = conn.cursor()

	# Check if albumId is unique
	cursor.execute("SELECT albumId FROM Albums WHERE albumId='{0}'".format(tempAlbumId))
	tempCheckId = cursor.fetchall()
	while (tempAlbumId == tempCheckId):
		cursor.execute("SELECT albumId FROM Albums WHERE albumId='{0}'".format(tempAlbumId))
		tempCheckId = cursor.fetchall()

	cursor.execute("INSERT INTO Albums (albumId,name,user_id,date_of_creation) VALUES ('{0}', '{1}', '{2}', NOW())".format(tempAlbumId, tempUserName, tempUserId))
	conn.commit()

	# Update the user's albums
	updatedAlbums = render_template('albums.html', albumList=list(getAllAlbumsFromUser() ))
	return updatedAlbums

def getAllAlbumsFromUser():
	print("getAllAlbumsFromUser()")
	# Grab user info
	tempUserId = getUserIdFromEmail(flask_login.current_user.id)

	# So we can select from the db
	cursor = conn.cursor()
	cursor.execute("SELECT * FROM Albums WHERE user_id = '{0}' ".format(tempUserId))
	allAlbums = cursor.fetchall()

	return allAlbums

@app.route('/deleteAlbum',methods=['GET','POST'])
def deleteAlbum():
	# Grab user and album info
	tempUserId = getUserIdFromEmail(flask_login.current_user.id)
	tempAlbumId = request.form.get("albumId")

	# So we can select from the db
	cursor = conn.cursor()

	# Get the user id
	cursor.execute("SELECT user_id FROM Albums WHERE albumId = '{0}'".format(tempAlbumId))
	checkUserId = str(cursor.fetchall())
	checkUserId = re.sub('[(),]','',checkUserId)

	if (str(tempUserId) == checkUserId):
		# Delete the assiciation with the tag
		cursor.execute("DELETE FROM PictureHasTag WHERE albumId = '{0}'".format(tempAlbumId))
		conn.commit()

		# Delete all likes associated with all pictures in the album
		cursor.execute("DELETE FROM Likes WHERE picture_id = (SELECT picture_id FROM Albums WHERE albumId = '{0}')".format(tempAlbumId))
		conn.commit()

		# Delete the pictures inside the album
		cursor.execute("DELETE FROM Pictures WHERE albumId = '{0}'".format(tempAlbumId))
		conn.commit()
		
		# Delete the album
		cursor.execute("DELETE FROM Albums WHERE albumId = '{0}'".format(tempAlbumId))
		conn.commit()

		# Reload the albums page
		tempUserAlbums = getAllAlbumsFromUser()
		return render_template('albums.html', albumList = tempUserAlbums)

	# Reload the unchanged page
	tempUserAlbums = getAllAlbumsFromUser()
	return render_template('albums.html', albumList = tempUserAlbums)

###################################################################
# Functions for pictures                                          #
###################################################################
@app.route('/openAlbum', methods=['GET','POST'])
def pictures():
	# Grab album info
	tempUserId  = getUserIdFromEmail(flask_login.current_user.id)
	tempAlbumId = request.args.get('albumId')

	# So we can selet from the db
	cursor = conn.cursor()
	cursor.execute("SELECT name FROM Albums WHERE albumId = '{0}'".format(tempAlbumId))
	tempAlbumName = str(cursor.fetchall())
	tempAlbumName = re.sub('[(),]','',tempAlbumName)

	# Grab the photos from the album
	cursor.execute("SELECT * FROM Pictures WHERE user_id='{0}' AND albumId='{1}'".format(tempUserId,tempAlbumId))
	tempListPhotos = pictureIntoFormat(list(cursor.fetchall()))

	return render_template('pictures.html', name=tempAlbumName, photoList=tempListPhotos, album=tempAlbumId)

def pictureIntoFormat(photos):
	tempNumPics = len(photos)
	# Get all the photos to disp them
	for i in range(tempNumPics):
		# Grab the photo
		tempPhoto = photos[i]

		# Grab data from the photo
		tempPicId   = tempPhoto[0]
		tempAlbumId = tempPhoto[1]
		tempUserId  = tempPhoto[2]
		tempImgData = tempPhoto[3]
		tempImgData = tempImgData.decode('ASCII')
		tempCap     = tempPhoto[4]

		# Get the tags
		cursor.execute("SELECT tag FROM PictureHasTag WHERE picture_id = '{0}'".format(tempPicId))
		tempTags = str(cursor.fetchall())
		tempTags = re.sub('[(),]','',tempTags)
		tempTags = re.sub("'", "", tempTags)

		# Get the likes
		cursor.execute("SELECT first, last FROM Users, Likes WHERE Likes.picture_id = '{0}' AND Users.user_id = Likes.user_id".format(tempPicId))
		tempLikes = list(cursor.fetchall())

		# Get comments
		cursor.execute("SELECT first, last, comment FROM Users, Comments WHERE picture_id = '{0}' AND Users.user_id = Comments.user_id".format(tempPicId))
		tempComms = list(cursor.fetchall())
		for j in range(0,len(tempComms)):
			tempComms[j] = re.sub('[(),]','',str(tempComms[j]))
			tempComms[j] = re.sub("'","",str(tempComms[j]))

		# Get num of likes
		numLikes = 0
		for j in tempLikes:
			numLikes += 1

		photos[i] = (tempPicId, tempAlbumId, tempUserId, tempImgData, tempCap, tempTags, tempLikes, tempComms, numLikes)

	return photos	

@app.route('/deletePicture', methods=['GET','POST'])
def deletePicture():
	# Grab user and picture info
	tempUserId = getUserIdFromEmail(flask_login.current_user.id)
	tempPicId = request.form.get("picture_id")
	tempAlbumId = request.form.get('albumId')

	# So we can select from the db
	cursor = conn.cursor()

	cursor.execute("SELECT user_id FROM Pictures WHERE picture_id = '{0}'".format(tempPicId))
	checkUserId = str(cursor.fetchall())
	checkUserId = re.sub('[(),]','',checkUserId)

	# Get album name
	cursor.execute("SELECT name FROM Albums WHERE albumId = '{0}'".format(tempAlbumId))
	tempAlbumName = str(cursor.fetchall())
	tempAlbumName = re.sub('[(),]','',tempAlbumName)

	if (str(tempUserId) == checkUserId):
		# Delete the association with the tag
		cursor.execute("DELETE FROM PictureHasTag WHERE picture_id = '{0}'".format(tempPicId))
		conn.commit()

		# Delete all associated likes
		cursor.execute("DELETE FROM Likes WHERE picture_id = '{0}'".format(tempPicId))
		conn.commit()

		# Delete the picture
		cursor.execute("DELETE FROM Pictures WHERE picture_id = '{0}'".format(tempPicId))
		conn.commit()

		# Reload the pictures page
		cursor.execute("SELECT * FROM Pictures WHERE user_id='{0}' AND albumId='{1}'".format(tempUserId,tempAlbumId))
		tempListPhotos = pictureIntoFormat(list(cursor.fetchall()))

		return render_template('pictures.html', name=tempAlbumName, photoList=tempListPhotos, album=tempAlbumId)

	print("missed the if")
	# Reload the pictures page
	cursor.execute("SELECT * FROM Pictures WHERE user_id='{0}' AND albumId='{1}'".format(tempUserId,tempAlbumId))
	tempListPhotos = pictureIntoFormat(list(cursor.fetchall()))

	return render_template('pictures.html', name=tempAlbumName, photoList=tempListPhotos, album=tempAlbumId)

@app.route('/addTag', methods=['GET','POST'])
def addTag():
	# Grab user and pic info
	tempUserId = getUserIdFromEmail(flask_login.current_user.id)
	tempPicId = request.form.get('picture_id')
	tempAlbumId = request.form.get('albumId')
	tempTag = request.form.get('tagText')

	cursor = conn.cursor()

	# Get the album name
	cursor.execute("SELECT name FROM Albums WHERE albumId = '{0}'".format(tempAlbumId))
	tempAlbumName = str(cursor.fetchall())
	tempAlbumName = re.sub('[(),]','',tempAlbumName)

	# If the picture already has the tag
	cursor.execute("SELECT tag FROM PictureHasTag WHERE picture_id='{0}'".format(tempPicId))
	tempCheckTags = list(cursor.fetchall())
	print("tempCheckTags: ", tempCheckTags)

	for i in tempCheckTags :
		i = i[0]
		print("i", i)
		if i == tempTag:
			print("tempTag: ", tempTag)
			# Grab all pictures from the page
			cursor.execute("SELECT * FROM Pictures WHERE user_id='{0}' AND albumId='{1}'".format(tempUserId,tempAlbumId))
			tempListPhotos = pictureIntoFormat(list(cursor.fetchall()))

			# Reload page
			return render_template('pictures.html', name=tempAlbumName, photoList=tempListPhotos, album=tempAlbumId)

	# Check if the tag exists
	cursor.execute("SELECT * FROM Tags WHERE tag = '{0}'".format(tempTag))
	tempCheckTagExists = str(cursor.fetchall())
	tempCheckTagExists = re.sub('[(),\']','',tempCheckTagExists)
	print("tempTag: ", tempTag)
	print("tempCheckTagExists: ", tempCheckTagExists)

	if (str(tempCheckTagExists) != tempTag):
		cursor.execute("INSERT INTO Tags VALUES ('{0}')".format(tempTag))
		conn.commit()
	else:
		print("Already exists")

	# Associate the tag with the picture
	cursor.execute("INSERT INTO PictureHasTag (picture_id, tag, albumId) VALUES ('{0}','{1}','{2}')".format(tempPicId, tempTag, tempAlbumId))
	conn.commit()

	# Grab all pictures from the page
	cursor.execute("SELECT * FROM Pictures WHERE user_id='{0}' AND albumId='{1}'".format(tempUserId,tempAlbumId))
	tempListPhotos = pictureIntoFormat(list(cursor.fetchall()))

	# Reload page
	return render_template('pictures.html', name=tempAlbumName, photoList=tempListPhotos, album=tempAlbumId)

@app.route('/removeTag', methods=['GET','POST'])
def removeTag():
	# Grab user and pic info
	tempUserId = getUserIdFromEmail(flask_login.current_user.id)
	tempPicId = request.form.get('picture_id')
	tempAlbumId = request.form.get('albumId')
	tempTag = request.form.get('deleteTagText')

	cursor = conn.cursor()

	# Get the album name
	cursor.execute("SELECT name FROM Albums WHERE albumId = '{0}'".format(tempAlbumId))
	tempAlbumName = str(cursor.fetchall())
	tempAlbumName = re.sub('[(),]','',tempAlbumName)

	# Get the user associated with the tag n picture
	cursor.execute("SELECT user_id FROM Pictures WHERE picture_id='{0}'".format(tempPicId))
	tempCheckUser = str(cursor.fetchall())
	tempCheckUser = re.sub('[(),\']','',tempCheckUser)

	if (str(tempCheckUser) == str(tempUserId)):
		print("tempTag: ", tempTag)
		print("tempPicId: ", tempPicId)
		cursor.execute("DELETE FROM PictureHasTag WHERE tag='{0}' AND picture_id='{1}'".format(tempTag,tempPicId))
		conn.commit()
	else:
		print("Not the same user")

	# Grab all pictures from the page
	cursor.execute("SELECT * FROM Pictures WHERE user_id='{0}' AND albumId='{1}'".format(tempUserId,tempAlbumId))
	tempListPhotos = pictureIntoFormat(list(cursor.fetchall()))

	# Reload page
	return render_template('pictures.html', name=tempAlbumName, photoList=tempListPhotos, album=tempAlbumId)

@app.route('/searchByTag', methods=['GET','POST'])
def searchByTag():
	tempTag = request.form.get('tagToSearch')

	cursor = conn.cursor()

	# Get all pic ids with matching tags
	cursor.execute("SELECT DISTINCT Pictures.picture_id, Pictures.albumId, user_id, imgdata, caption FROM Pictures, PictureHasTag WHERE PictureHasTag.tag='{0}'".format(tempTag))
	tempy = list(cursor.fetchall())

	tempDispPhotos = pictureIntoFormat(tempy)

	return render_template('searchByTag.html', photoList=tempDispPhotos, tagName=tempTag)
	
@app.route('/searchMyPicsByTag', methods=['GET','POST'])
def searchMyPicsByTag():
	tempUserId = getUserIdFromEmail(flask_login.current_user.id)
	tempTag = request.form.get('tagToSearch')

	cursor = conn.cursor()

	# Get all pic ids with matching tags
	cursor.execute("SELECT DISTINCT Pictures.picture_id, Pictures.albumId, user_id, imgdata, caption FROM Pictures, PictureHasTag WHERE PictureHasTag.tag='{0}' AND Pictures.user_id='{1}'".format(tempTag,tempUserId))
	tempy = list(cursor.fetchall())

	tempDispPhotos = pictureIntoFormat(tempy)

	return render_template('searchMyPicsByTag.html', photoList=tempDispPhotos)

@app.route('/viewPopularTags', methods=['GET','POST'])
def viewPopularTags():
	cursor = conn.cursor()

	# Get popular tags
	cursor.execute("SELECT Pictures.picture_id, Pictures.albumId, user_id, imgdata, caption FROM Pictures, PictureHasTag GROUP BY Pictures.picture_id ORDER BY COUNT(PictureHasTag.tag) DESC")
	tempTopTags = pictureIntoFormat(list(cursor.fetchall()))

	return render_template('viewPopularTags.html', photoList=tempTopTags)

@app.route('/recommendTags', methods=['GET','POST'])
def recommendTags():
	# Grab user and pic info
	tempUserId = getUserIdFromEmail(flask_login.current_user.id)
	tempPicId = request.form.get('picture_id')
	tempAlbumId = request.form.get('albumId')
	tempTag = request.form.get('tagText')

	cursor = conn.cursor()

	# Get the album name
	cursor.execute("SELECT name FROM Albums WHERE albumId = '{0}'".format(tempAlbumId))
	tempAlbumName = str(cursor.fetchall())
	tempAlbumName = re.sub('[(),]','',tempAlbumName)

	# Get the user associated with the tag n picture
	cursor.execute("SELECT user_id FROM Pictures WHERE picture_id='{0}'".format(tempPicId))
	tempCheckUser = str(cursor.fetchall())
	tempCheckUser = re.sub('[(),\']','',tempCheckUser)

	# Grab all pictures from the page
	cursor.execute("SELECT * FROM Pictures WHERE user_id='{0}' AND albumId='{1}'".format(tempUserId,tempAlbumId))
	tempListPhotos = pictureIntoFormat(list(cursor.fetchall()))

	if(str(tempUserId)==str(tempCheckUser)):
		# Find all the photos that contain these tags
		# Take the tags of these photos in the result set and order them by frequency of occurrence
		cursor.execute("SELECT picture_id FROM PictureHasTag WHERE tag='{0}'".format(tempTag))
		tempPics = cursor.fetchall()

		tempy = []
		for i in tempPics:
			tempy.append(i[0])
		tempPics = tempy
		tempy = []

		for i in tempPics:
			cursor.execute("SELECT tag FROM PictureHasTag WHERE picture_id='{0}' GROUP BY tag ORDER BY COUNT(tag)".format(i))
			tempy.append(cursor.fetchall())

		tempPopularTag = tempy[0][0][0]

		return render_template('pictures.html', name=tempAlbumName, photoList=tempListPhotos, album=tempAlbumId, recommendTags=tempPopularTag)
	else:
		return render_template('pictures.html', name=tempAlbumName, photoList=tempListPhotos, album=tempAlbumId)

@app.route('/loadChangeProfile', methods=['GET','POST'])
def loadChangeProfile():
	return render_template('changeProfilePic.html')

@app.route('/changeProfile',methods=['GET','POST'])
def changeProfile():
	# Grab user info
	tempUserId = getUserIdFromEmail(flask_login.current_user.id)
	# get new pic 
	proPic = request.form.get('photo')

	cursor = conn.cursor()
	# Check if old pic exists
	cursor.execute("UPDATE Users SET profilePic='{0}' WHERE user_id='{1}'".format(proPic,tempUserId))
	conn.commit()


	return render_template('hello.html')


###################################################################
# Functions for likes and comments                                #
###################################################################
@app.route('/postComment', methods=['GET','POST'])
def postComment():
	if(flask_login.current_user.is_anonymous==False):
		# Grab user and pic info
		tempUserId = getUserIdFromEmail(flask_login.current_user.id)
		tempPicId = request.form.get('picture_id')
		tempCommId = int(random.uniform(1,999999))
		tempComm = request.form.get('commentText')
		tempAlbumId = request.form.get('albumId')

		cursor = conn.cursor()

		# Check if comm_id is unique
		cursor.execute("SELECT comm_id FROM Comments WHERE comm_id='{0}'".format(tempCommId))
		tempCheckId = cursor.fetchall()
		while (tempCommId == tempCheckId):
			cursor.execute("SELECT comm_id FROM Comments WHERE comm_id='{0}'".format(tempCommId))
			tempCheckId = cursor.fetchall()

		# Get the album name
		cursor.execute("SELECT name FROM Albums WHERE albumId = '{0}'".format(tempAlbumId))
		tempAlbumName = str(cursor.fetchall())
		tempAlbumName = re.sub('[(),]','',tempAlbumName)

		# Check if the user is commenting on their own post
		cursor.execute("SELECT user_id FROM Pictures WHERE picture_id='{0}'".format(tempPicId))
		tempCheckUser = str(cursor.fetchall())
		tempCheckUser = re.sub('[(),]','',tempCheckUser)
		print("tempCheckUser: ", tempCheckUser)
		print("tempUserId: ", tempUserId)

		if(str(tempUserId) == str(tempCheckUser)):
			print("Can't comment")
			# Grab all pictures from the page
			cursor.execute("SELECT * FROM Pictures WHERE user_id='{0}' AND albumId='{1}'".format(tempUserId,tempAlbumId))
			tempListPhotos = pictureIntoFormat(list(cursor.fetchall()))

			# Reload page
			return render_template('pictures.html', name=tempAlbumName, photoList=tempListPhotos, album=tempAlbumId)
		else:

			# Insert the comment
			cursor.execute("INSERT INTO Comments (comm_id, comment, user_id, picture_id, commDate) VALUES ('{0}','{1}','{2}','{3}',NOW())".format(tempCommId, tempComm, tempUserId, tempPicId))
			conn.commit()

			# Grab all pictures from the page
			cursor.execute("SELECT * FROM Pictures WHERE user_id='{0}' AND albumId='{1}'".format(tempUserId,tempAlbumId))
			tempListPhotos = pictureIntoFormat(list(cursor.fetchall()))

			# Reload page
			return render_template('pictures.html', name=tempAlbumName, photoList=tempListPhotos, album=tempAlbumId)
	else:
		tempPicId = request.form.get('picture_id')
		tempCommId = int(random.uniform(1,999999))
		tempComm = request.form.get('commentText')
		tempAlbumId = request.form.get('albumId')

		cursor = conn.cursor()

		# Check if comm_id is unique
		cursor.execute("SELECT comm_id FROM Comments WHERE comm_id='{0}'".format(tempCommId))
		tempCheckId = cursor.fetchall()
		while (tempCommId == tempCheckId):
			cursor.execute("SELECT comm_id FROM Comments WHERE comm_id='{0}'".format(tempCommId))
			tempCheckId = cursor.fetchall()

		# Get the album name
		cursor.execute("SELECT name FROM Albums WHERE albumId = '{0}'".format(tempAlbumId))
		tempAlbumName = str(cursor.fetchall())
		tempAlbumName = re.sub('[(),]','',tempAlbumName)

		tempUserId = int(random.uniform(1,999999))

		# Check if user_id is unique
		cursor.execute("SELECT user_id FROM Users WHERE user_id='{0}'".format(tempUserId))
		tempCheckId = cursor.fetchall()
		while (tempUserId == tempCheckId):
			cursor.execute("SELECT user_id FROM Users WHERE user_id='{0}'".format(tempUserId))
			tempCheckId = cursor.fetchall()

		# Generate anon id
		cursor.execute("INSERT INTO Users (user_id, first) VALUES ('{0}','anon')".format(tempUserId))
		conn.commit()

		# Insert the comment
		cursor.execute("INSERT INTO Comments (comm_id, comment, user_id, picture_id, commDate) VALUES ('{0}','{1}','{2}','{3}',NOW())".format(tempCommId, tempComm, tempUserId, tempPicId))
		conn.commit()

		# Grab all pictures from the page
		cursor.execute("SELECT * FROM Pictures WHERE user_id='{0}' AND albumId='{1}'".format(tempUserId,tempAlbumId))
		tempListPhotos = pictureIntoFormat(list(cursor.fetchall()))

		# Reload page
		return render_template('pictures.html', name=tempAlbumName, photoList=tempListPhotos, album=tempAlbumId)

@app.route('/postCommentTag', methods=['GET','POST'])
def postCommentTag():
	if(flask_login.current_user.is_anonymous==False):
		# Grab user and pic info
		tempUserId = getUserIdFromEmail(flask_login.current_user.id)
		tempPicId = request.form.get('picture_id')
		tempCommId = int(random.uniform(1,999999))
		tempComm = request.form.get('commentText')

		cursor = conn.cursor()

		# Check if comm_id is unique
		cursor.execute("SELECT comm_id FROM Comments WHERE comm_id='{0}'".format(tempCommId))
		tempCheckId = cursor.fetchall()
		while (tempCommId == tempCheckId):
			cursor.execute("SELECT comm_id FROM Comments WHERE comm_id='{0}'".format(tempCommId))
			tempCheckId = cursor.fetchall()

		# Check if the user is commenting on their own post
		cursor.execute("SELECT user_id FROM Pictures WHERE picture_id='{0}'".format(tempPicId))
		tempCheckUser = str(cursor.fetchall())
		tempCheckUser = re.sub('[(),]','',tempCheckUser)

		if(str(tempUserId) == str(tempCheckUser)):
			print("Can't comment")
			# Grab all pictures from the page
			cursor.execute("SELECT * FROM Pictures WHERE user_id='{0}' AND albumId='{1}'".format(tempUserId,tempAlbumId))
			tempListPhotos = pictureIntoFormat(list(cursor.fetchall()))
			tempTag = request.form.get('tagName')

			# Get all pic ids with matching tags
			cursor.execute("SELECT DISTINCT Pictures.picture_id, Pictures.albumId, user_id, imgdata, caption FROM Pictures, PictureHasTag WHERE PictureHasTag.tag='{0}'".format(tempTag))
			tempy = list(cursor.fetchall())

			tempDispPhotos = pictureIntoFormat(tempy)

			print(tempTag)
			return render_template('searchByTag.html', photoList=tempDispPhotos, tagName=tempTag)
		else:
			print("hello")
			# Insert the comment
			cursor.execute("INSERT INTO Comments (comm_id, comment, user_id, picture_id, commDate) VALUES ('{0}','{1}','{2}','{3}',NOW())".format(tempCommId, tempComm, tempUserId, tempPicId))
			conn.commit()

			tempTag = request.form.get('tagName')

			# Get all pic ids with matching tags
			cursor.execute("SELECT DISTINCT Pictures.picture_id, Pictures.albumId, user_id, imgdata, caption FROM Pictures, PictureHasTag WHERE PictureHasTag.tag='{0}'".format(tempTag))
			tempy = list(cursor.fetchall())

			tempDispPhotos = pictureIntoFormat(tempy)

			print(tempTag)
			return render_template('searchByTag.html', photoList=tempDispPhotos, tagName=tempTag)
	else:
		tempPicId = request.form.get('picture_id')
		tempCommId = int(random.uniform(1,999999))
		tempComm = request.form.get('commentText')
		tempAlbumId = request.form.get('albumId')

		cursor = conn.cursor()

		# Check if comm_id is unique
		cursor.execute("SELECT comm_id FROM Comments WHERE comm_id='{0}'".format(tempCommId))
		tempCheckId = cursor.fetchall()
		while (tempCommId == tempCheckId):
			cursor.execute("SELECT comm_id FROM Comments WHERE comm_id='{0}'".format(tempCommId))
			tempCheckId = cursor.fetchall()

		# Get the album name
		cursor.execute("SELECT name FROM Albums WHERE albumId = '{0}'".format(tempAlbumId))
		tempAlbumName = str(cursor.fetchall())
		tempAlbumName = re.sub('[(),]','',tempAlbumName)

		tempUserId = int(random.uniform(1,999999))

		# Check if user_id is unique
		cursor.execute("SELECT user_id FROM Users WHERE user_id='{0}'".format(tempUserId))
		tempCheckId = cursor.fetchall()
		while (tempUserId == tempCheckId):
			cursor.execute("SELECT user_id FROM Users WHERE user_id='{0}'".format(tempUserId))
			tempCheckId = cursor.fetchall()

		# Generate anon id
		cursor.execute("INSERT INTO Users (user_id, first) VALUES ('{0}','anon')".format(tempUserId))
		conn.commit()

		# Insert the comment
		cursor.execute("INSERT INTO Comments (comm_id, comment, user_id, picture_id, commDate) VALUES ('{0}','{1}','{2}','{3}',NOW())".format(tempCommId, tempComm, tempUserId, tempPicId))
		conn.commit()

		tempTag = request.form.get('tagName')

		# Get all pic ids with matching tags
		cursor.execute("SELECT DISTINCT Pictures.picture_id, Pictures.albumId, user_id, imgdata, caption FROM Pictures, PictureHasTag WHERE PictureHasTag.tag='{0}'".format(tempTag))
		tempy = list(cursor.fetchall())

		tempDispPhotos = pictureIntoFormat(tempy)

		print(tempTag)
		return render_template('searchByTag.html', photoList=tempDispPhotos, tagName=tempTag)

@app.route('/postCommentPopular', methods=['GET','POST'])
def postCommentPopular():
	if(flask_login.current_user.is_anonymous==False):
		# Grab user and pic info
		tempUserId = getUserIdFromEmail(flask_login.current_user.id)
		tempPicId = request.form.get('picture_id')
		tempCommId = int(random.uniform(1,999999))
		tempComm = request.form.get('commentText')

		cursor = conn.cursor()

		# Check if comm_id is unique
		cursor.execute("SELECT comm_id FROM Comments WHERE comm_id='{0}'".format(tempCommId))
		tempCheckId = cursor.fetchall()
		while (tempCommId == tempCheckId):
			cursor.execute("SELECT comm_id FROM Comments WHERE comm_id='{0}'".format(tempCommId))
			tempCheckId = cursor.fetchall()

		# Check if the user is commenting on their own post
		cursor.execute("SELECT user_id FROM Pictures WHERE picture_id='{0}'".format(tempPicId))
		tempCheckUser = str(cursor.fetchall())
		tempCheckUser = re.sub('[(),]','',tempCheckUser)

		if(str(tempUserId) == str(tempCheckUser)):
			print("Can't comment")
			# Grab all pictures from the page
			cursor.execute("SELECT * FROM Pictures WHERE user_id='{0}' AND albumId='{1}'".format(tempUserId,tempAlbumId))
			tempListPhotos = pictureIntoFormat(list(cursor.fetchall()))
			
			# Get popular tags
			cursor.execute("SELECT Pictures.picture_id, Pictures.albumId, user_id, imgdata, caption FROM Pictures, PictureHasTag GROUP BY Pictures.picture_id ORDER BY COUNT(PictureHasTag.tag) DESC")
			tempTopTags = pictureIntoFormat(list(cursor.fetchall()))

			return render_template('viewPopularTags.html', photoList=tempTopTags)

		else:
			print("hello")
			# Insert the comment
			cursor.execute("INSERT INTO Comments (comm_id, comment, user_id, picture_id, commDate) VALUES ('{0}','{1}','{2}','{3}',NOW())".format(tempCommId, tempComm, tempUserId, tempPicId))
			conn.commit()

			# Get popular tags
			cursor.execute("SELECT Pictures.picture_id, Pictures.albumId, user_id, imgdata, caption FROM Pictures, PictureHasTag GROUP BY Pictures.picture_id ORDER BY COUNT(PictureHasTag.tag) DESC")
			tempTopTags = pictureIntoFormat(list(cursor.fetchall()))

			return render_template('viewPopularTags.html', photoList=tempTopTags)
	else:
		tempPicId = request.form.get('picture_id')
		tempCommId = int(random.uniform(1,999999))
		tempComm = request.form.get('commentText')
		tempAlbumId = request.form.get('albumId')

		cursor = conn.cursor()

		# Check if comm_id is unique
		cursor.execute("SELECT comm_id FROM Comments WHERE comm_id='{0}'".format(tempCommId))
		tempCheckId = cursor.fetchall()
		while (tempCommId == tempCheckId):
			cursor.execute("SELECT comm_id FROM Comments WHERE comm_id='{0}'".format(tempCommId))
			tempCheckId = cursor.fetchall()

		# Get the album name
		cursor.execute("SELECT name FROM Albums WHERE albumId = '{0}'".format(tempAlbumId))
		tempAlbumName = str(cursor.fetchall())
		tempAlbumName = re.sub('[(),]','',tempAlbumName)

		tempUserId = int(random.uniform(1,999999))

		# Check if user_id is unique
		cursor.execute("SELECT user_id FROM Users WHERE user_id='{0}'".format(tempUserId))
		tempCheckId = cursor.fetchall()
		while (tempUserId == tempCheckId):
			cursor.execute("SELECT user_id FROM Users WHERE user_id='{0}'".format(tempUserId))
			tempCheckId = cursor.fetchall()

		# Generate anon id
		cursor.execute("INSERT INTO Users (user_id, first) VALUES ('{0}','anon')".format(tempUserId))
		conn.commit()

		# Insert the comment
		cursor.execute("INSERT INTO Comments (comm_id, comment, user_id, picture_id, commDate) VALUES ('{0}','{1}','{2}','{3}',NOW())".format(tempCommId, tempComm, tempUserId, tempPicId))
		conn.commit()

		# Get popular tags
		cursor.execute("SELECT Pictures.picture_id, Pictures.albumId, user_id, imgdata, caption FROM Pictures, PictureHasTag GROUP BY Pictures.picture_id ORDER BY COUNT(PictureHasTag.tag) DESC")
		tempTopTags = pictureIntoFormat(list(cursor.fetchall()))

		return render_template('viewPopularTags.html', photoList=tempTopTags)

@app.route('/likePicture', methods=['GET','POST'])
def likePicture():
	# Get user information
	if(flask_login.current_user.is_anonymous==False):
		tempUserId = getUserIdFromEmail(flask_login.current_user.id)
		tempPicId = request.form.get('picture_id')
		tempAlbumId = request.form.get('albumId')

		cursor = conn.cursor()

		# Get the album name
		cursor.execute("SELECT name FROM Albums WHERE albumId = '{0}'".format(tempAlbumId))
		tempAlbumName = str(cursor.fetchall())
		tempAlbumName = re.sub('[(),]','',tempAlbumName)

		# Check if pic is already liked
		cursor.execute("SELECT user_id FROM Likes WHERE user_id = '{0}' AND picture_id = '{1}'".format(tempUserId,tempPicId))
		checkUserId = str(cursor.fetchall())
		checkUserId = re.sub('[(),]','',checkUserId)

		# If the user has already liked the photo, refresh the page
		if(str(tempUserId) == checkUserId):
			# Grab all pictures from the page
			cursor.execute("SELECT * FROM Pictures WHERE user_id='{0}' AND albumId='{1}'".format(tempUserId,tempAlbumId))
			tempListPhotos = pictureIntoFormat(list(cursor.fetchall()))

			# Reload the pictures page
			return render_template('pictures.html', name=tempAlbumName, photoList=tempListPhotos, album=tempAlbumId)
		else: 
			# Insert into likes table 
			cursor.execute("INSERT INTO Likes (user_id, picture_id) VALUES ('{0}','{1}')".format(tempUserId,tempPicId))
			conn.commit()

			# Grab all pictures from the page
			cursor.execute("SELECT * FROM Pictures WHERE user_id='{0}' AND albumId='{1}'".format(tempUserId,tempAlbumId))
			tempListPhotos = pictureIntoFormat(list(cursor.fetchall()))

			# Reload page
			return render_template('pictures.html', name=tempAlbumName, photoList=tempListPhotos, album=tempAlbumId)
	else:
		tempPicId = request.form.get('picture_id')
		tempAlbumId = request.form.get('albumId')

		cursor = conn.cursor()

		# Get the album name
		cursor.execute("SELECT name FROM Albums WHERE albumId = '{0}'".format(tempAlbumId))
		tempAlbumName = str(cursor.fetchall())
		tempAlbumName = re.sub('[(),]','',tempAlbumName)

		tempUserId = int(random.uniform(1,999999))

		# Check if user_id is unique
		cursor.execute("SELECT user_id FROM Users WHERE user_id='{0}'".format(tempUserId))
		tempCheckId = cursor.fetchall()
		while (tempUserId == tempCheckId):
			cursor.execute("SELECT user_id FROM Users WHERE user_id='{0}'".format(tempUserId))
			tempCheckId = cursor.fetchall()

		# Generate anon id
		cursor.execute("INSERT INTO Users (user_id, first) VALUES ('{0}','anon')".format(tempUserId))
		conn.commit()

		# Insert into likes table 
		cursor.execute("INSERT INTO Likes (user_id, picture_id) VALUES ('{0}','{1}')".format(tempUserId,tempPicId))
		conn.commit()

		# Grab all pictures from the page
		cursor.execute("SELECT * FROM Pictures WHERE user_id='{0}' AND albumId='{1}'".format(tempUserId,tempAlbumId))
		tempListPhotos = pictureIntoFormat(list(cursor.fetchall()))

		# Reload page
		return render_template('pictures.html', name=tempAlbumName, photoList=tempListPhotos, album=tempAlbumId)

@app.route('/likePictureTag', methods=['GET','POST'])
def likePictureTag():
	# Get user information
	if(flask_login.current_user.is_anonymous==False):
		tempUserId = getUserIdFromEmail(flask_login.current_user.id)
		tempPicId = request.form.get('picture_id')
		tempAlbumId = request.form.get('albumId')

		cursor = conn.cursor()

		# Get the album name
		cursor.execute("SELECT name FROM Albums WHERE albumId = '{0}'".format(tempAlbumId))
		tempAlbumName = str(cursor.fetchall())
		tempAlbumName = re.sub('[(),]','',tempAlbumName)

		# Check if pic is already liked
		cursor.execute("SELECT user_id FROM Likes WHERE user_id = '{0}' AND picture_id = '{1}'".format(tempUserId,tempPicId))
		checkUserId = str(cursor.fetchall())
		checkUserId = re.sub('[(),]','',checkUserId)

		# If the user has already liked the photo, refresh the page
		if(str(tempUserId) == checkUserId):
			tempTag = request.form.get('tagName')

			# Get all pic ids with matching tags
			cursor.execute("SELECT DISTINCT Pictures.picture_id, Pictures.albumId, user_id, imgdata, caption FROM Pictures, PictureHasTag WHERE PictureHasTag.tag='{0}'".format(tempTag))
			tempy = list(cursor.fetchall())

			tempDispPhotos = pictureIntoFormat(tempy)

			print(tempTag)
			return render_template('searchByTag.html', photoList=tempDispPhotos, tagName=tempTag)
		else: 
			# Insert into likes table 
			cursor.execute("INSERT INTO Likes (user_id, picture_id) VALUES ('{0}','{1}')".format(tempUserId,tempPicId))
			conn.commit()

			tempTag = request.form.get('tagName')

			# Get all pic ids with matching tags
			cursor.execute("SELECT DISTINCT Pictures.picture_id, Pictures.albumId, user_id, imgdata, caption FROM Pictures, PictureHasTag WHERE PictureHasTag.tag='{0}'".format(tempTag))
			tempy = list(cursor.fetchall())

			tempDispPhotos = pictureIntoFormat(tempy)

			print(tempTag)
			return render_template('searchByTag.html', photoList=tempDispPhotos, tagName=tempTag)
	else:
		tempPicId = request.form.get('picture_id')
		tempAlbumId = request.form.get('albumId')

		cursor = conn.cursor()

		# Get the album name
		cursor.execute("SELECT name FROM Albums WHERE albumId = '{0}'".format(tempAlbumId))
		tempAlbumName = str(cursor.fetchall())
		tempAlbumName = re.sub('[(),]','',tempAlbumName)

		tempUserId = int(random.uniform(1,999999))

		# Check if user_id is unique
		cursor.execute("SELECT user_id FROM Users WHERE user_id='{0}'".format(tempUserId))
		tempCheckId = cursor.fetchall()
		while (tempUserId == tempCheckId):
			cursor.execute("SELECT user_id FROM Users WHERE user_id='{0}'".format(tempUserId))
			tempCheckId = cursor.fetchall()

		# Generate anon id
		cursor.execute("INSERT INTO Users (user_id, first) VALUES ('{0}','anon')".format(tempUserId))
		conn.commit()

		# Insert into likes table 
		cursor.execute("INSERT INTO Likes (user_id, picture_id) VALUES ('{0}','{1}')".format(tempUserId,tempPicId))
		conn.commit()

		tempTag = request.form.get('tagName')

		# Get all pic ids with matching tags
		cursor.execute("SELECT DISTINCT Pictures.picture_id, Pictures.albumId, user_id, imgdata, caption FROM Pictures, PictureHasTag WHERE PictureHasTag.tag='{0}'".format(tempTag))
		tempy = list(cursor.fetchall())

		tempDispPhotos = pictureIntoFormat(tempy)

		print(tempTag)
		return render_template('searchByTag.html', photoList=tempDispPhotos, tagName=tempTag)

@app.route('/likePicturePopular', methods=['GET','POST'])
def likePicturePopular():
	# Get user information
	if(flask_login.current_user.is_anonymous==False):
		tempUserId = getUserIdFromEmail(flask_login.current_user.id)
		tempPicId = request.form.get('picture_id')
		tempAlbumId = request.form.get('albumId')

		cursor = conn.cursor()

		# Get the album name
		cursor.execute("SELECT name FROM Albums WHERE albumId = '{0}'".format(tempAlbumId))
		tempAlbumName = str(cursor.fetchall())
		tempAlbumName = re.sub('[(),]','',tempAlbumName)

		# Check if pic is already liked
		cursor.execute("SELECT user_id FROM Likes WHERE user_id = '{0}' AND picture_id = '{1}'".format(tempUserId,tempPicId))
		checkUserId = str(cursor.fetchall())
		checkUserId = re.sub('[(),]','',checkUserId)

		# If the user has already liked the photo, refresh the page
		if(str(tempUserId) == checkUserId):
			# Get popular tags
			cursor.execute("SELECT Pictures.picture_id, Pictures.albumId, user_id, imgdata, caption FROM Pictures, PictureHasTag GROUP BY Pictures.picture_id ORDER BY COUNT(PictureHasTag.tag) DESC")
			tempTopTags = pictureIntoFormat(list(cursor.fetchall()))

			return render_template('viewPopularTags.html', photoList=tempTopTags)
		else: 
			# Insert into likes table 
			cursor.execute("INSERT INTO Likes (user_id, picture_id) VALUES ('{0}','{1}')".format(tempUserId,tempPicId))
			conn.commit()

			# Get popular tags
			cursor.execute("SELECT Pictures.picture_id, Pictures.albumId, user_id, imgdata, caption FROM Pictures, PictureHasTag GROUP BY Pictures.picture_id ORDER BY COUNT(PictureHasTag.tag) DESC")
			tempTopTags = pictureIntoFormat(list(cursor.fetchall()))

			return render_template('viewPopularTags.html', photoList=tempTopTags)
	else:
		tempPicId = request.form.get('picture_id')
		tempAlbumId = request.form.get('albumId')

		cursor = conn.cursor()

		# Get the album name
		cursor.execute("SELECT name FROM Albums WHERE albumId = '{0}'".format(tempAlbumId))
		tempAlbumName = str(cursor.fetchall())
		tempAlbumName = re.sub('[(),]','',tempAlbumName)

		tempUserId = int(random.uniform(1,999999))

		# Check if user_id is unique
		cursor.execute("SELECT user_id FROM Users WHERE user_id='{0}'".format(tempUserId))
		tempCheckId = cursor.fetchall()
		while (tempUserId == tempCheckId):
			cursor.execute("SELECT user_id FROM Users WHERE user_id='{0}'".format(tempUserId))
			tempCheckId = cursor.fetchall()

		# Generate anon id
		cursor.execute("INSERT INTO Users (user_id, first) VALUES ('{0}','anon')".format(tempUserId))
		conn.commit()

		# Insert into likes table 
		cursor.execute("INSERT INTO Likes (user_id, picture_id) VALUES ('{0}','{1}')".format(tempUserId,tempPicId))
		conn.commit()

		# Get popular tags
		cursor.execute("SELECT Pictures.picture_id, Pictures.albumId, user_id, imgdata, caption FROM Pictures, PictureHasTag GROUP BY Pictures.picture_id ORDER BY COUNT(PictureHasTag.tag) DESC")
		tempTopTags = pictureIntoFormat(list(cursor.fetchall()))

		return render_template('viewPopularTags.html', photoList=tempTopTags)
###################################################################
# Functions for friends                                           #
###################################################################
@app.route('/friends', methods=['GET','POST'])
def friends():
	currentFriends = getFriends()
	print("currentFriends: ", currentFriends)
	return render_template('friends.html', usersFriends=currentFriends)

@app.route('/searchUsers', methods=['GET','POST'])
def searchUsers():
	# Grab info from search
	tempUserToSearch = str(request.form.get("userToSearch"))
	tempUserToSearch = tempUserToSearch.split()

	cursor = conn.cursor()

	# Find all users with matching first names or last names
	if len(tempUserToSearch) == 1:
		cursor.execute("SELECT first, last, email, user_id FROM Users WHERE last LIKE '{0}'".format(tempUserToSearch[0]))
		tempFirst = list(cursor.fetchall())
		
		cursor.execute("SELECT first, last, email, user_id FROM Users WHERE first LIKE '{0}'".format(tempUserToSearch[0]))
		tempLast = list(cursor.fetchall())
		friendsList = tempFirst + tempLast
	elif len(tempUserToSearch) == 2:
		cursor.execute("SELECT first, last, email, user_id FROM Users WHERE last LIKE '{0}' AND first LIKE '{1}'".format(tempUserToSearch[0],tempUserToSearch[1]))
		tempFirst = list(cursor.fetchall())
		
		cursor.execute("SELECT first, last, email, user_id FROM Users WHERE first LIKE '{0}' AND last LIKE '{1}'".format(tempUserToSearch[0],tempUserToSearch[1]))
		tempLast = list(cursor.fetchall())
		friendsList = tempFirst + tempLast

	currentFriends = getFriends()
	print("currentFriends: ", currentFriends)
	return render_template('friends.html', usersFriends=currentFriends, friends=friendsList)

@app.route('/addFriend', methods=['GET','POST'])
def addFriend():
	# Grab user and add user info
	tempUserId = getUserIdFromEmail(flask_login.current_user.id)
	tempAddId = request.form.get('user_id')

	cursor = conn.cursor()
	cursor.execute("SELECT * FROM Friends WHERE user_id1 = '{0}' AND user_id2 = '{1}'".format(tempUserId, tempAddId))
	tempCheckFriends = cursor.fetchall()
	# If the users are not friends yet
	if(len(tempCheckFriends)==0):
		cursor.execute("INSERT INTO Friends (user_id1, user_id2) VALUES ('{0}','{1}')".format(tempUserId, tempAddId))

	conn.commit()
	currentFriends = getFriends()
	print("currentFriends: ", currentFriends)
	return render_template('friends.html', usersFriends=currentFriends)

def getFriends():
	tempUserId = getUserIdFromEmail(flask_login.current_user.id)

	cursor = conn.cursor()
	cursor.execute("SELECT first, last, email, user_id FROM Users, Friends WHERE Friends.user_id1 = '{}' AND Users.user_id = Friends.user_id2".format(tempUserId))
	
	return cursor.fetchall()

###################################################################
# Functions for recommendations                                   #
###################################################################

@app.route('/top10Users', methods=['GET','POST'])
def top10Users():
	# Order the users by number of uploads and comments
	cursor = conn.cursor()
	cursor.execute("SELECT Users.first, Users.last FROM Users, Pictures, Comments WHERE Pictures.user_id = Users.user_id AND Users.user_id = Comments.user_id GROUP BY Users.user_id ORDER BY COUNT(Pictures.picture_id) LIMIT 10")
	tempTopUsers = list(cursor.fetchall())

	tempDispUsers = []

	# Get the first and last names of the top users
	for i in range(len(tempTopUsers)):
		print(tempDispUsers.append(str(tempTopUsers[i][0])+" "+str(tempTopUsers[i][1])))

	return render_template('top10users.html', top10Users = tempDispUsers)

#default page  
@app.route("/", methods=['GET'])
def hello():
	return render_template('hello.html', message='Welcome to Photoshare')


if __name__ == "__main__":
	#this is invoked when in the shell  you run 
	#$ python app.py 
	app.run(port=5000, debug=True)
