from flask import Flask , request, jsonify, make_response 
from flask_sqlalchemy import SQLAlchemy 
from  werkzeug.security import generate_password_hash, check_password_hash
import jwt, json  

from sqlalchemy import text
app = Flask(__name__)
app.config['SECRET_KEY'] = '7074a75c-885e-4103-8b5f-9251b979215e'
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://vipin:vkp1985mom@imdb-vips.cgfwfhrnonk2.us-east-2.rds.amazonaws.com:3306/imdb'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True
db = SQLAlchemy(app)
@app.before_first_request
def before_first_request_func():
	db.create_all()


class Users(db.Model):
	user_id  = db.Column(db.Integer , primary_key = True)
	name     = db.Column(db.String(100), nullable = False)
	email    = db.Column(db.String(100), unique = True , nullable = False)
	password = db.Column(db.String(100))
	is_admin = db.Column(db.Boolean ,  default=False)
	is_active = db.Column(db.Boolean, default = True)


class ImdbMovie(db.Model):
	mv_id = db.Column(db.Integer , primary_key = True)
	popularity = db.Column(db.Float , nullable = False) 
	director   = db.Column(db.String(100), nullable = False)
	imdb_score = db.Column(db.Float , nullable = False, default = 0 )
	name       = db.Column(db.String(100), nullable = False)
	genre      = db.Column(db.Text ,  nullable = False )
	added_by   = db.Column(db.Integer , db.ForeignKey('users.user_id'))

def verify_token(func):
	def inner(*args, **kwargs):
		token = None
		if request.headers.get('AUTH-TOKEN'):
			token = request.headers.get('AUTH-TOKEN')
		if not token:
			return jsonify({'message' : 'Token is missing !!'}), 401
		
		user = None
		try:
			payload = jwt.decode(token,app.config['SECRET_KEY'] )
			user = Users.query.get(payload.get('user_id'))
		except Exception as e:
			return make_response('Token is invalid !!' + str(e), 401)

		access_method = func.__name__
		if not user.is_admin and access_method in ['add_movie','edit_movie']:
			return make_response('Only admin can do these operations!!', 401)
		else:
			return func(user.user_id, *args,**kwargs)
	return inner
		
@app.route("/auth/register" , methods = ['GET', 'POST'])
def register_user():
	if request.method == 'POST':
		params = request.json
		user = Users.query.filter_by(name = params['username'],email = params['email']).first()

		if not user:
			is_admin = params.get('is_admin') or 0
			try:
				user = Users(
					    name     = params['username'], 
				    	    email    = params['email'] ,
				            password = generate_password_hash(params['password']),
				            is_admin = is_admin
					  )
			  
				db.session.add(user)
				db.session.commit() 
			except Exception as e:
				return  make_response( 'Internal Server Error', 500 )  
			
			return  make_response('Successfully Registered!', 201 )  
		else:
			return make_response('User already exists. Please Log in.', 202)
			

@app.route("/auth/token" , methods = ['GET', 'POST'])
def get_token():
	params = request.json
	if not params.get('email') and not params.get('password'):
		return make_response('Email and password are mandatory to login.', 202)
	
	user = Users.query.filter_by(email = params.get('email')).first()
	if not user:
		return make_response('User does not exists.', 401)
	
	verify_pass = check_password_hash(user.password ,params.get('password'))
	if verify_pass:
		token = jwt.encode({'user_id':user.user_id, 'is_admin':user.is_admin} ,app.config['SECRET_KEY'])
		return make_response(jsonify({'token' : token.decode('UTF-8')}), 201)
	else:
		return {'a':1}


@app.route("/imdb/add" , methods = ['GET', 'POST'])
@verify_token
def add_movie(user_id):
	if request.method == 'POST':
		params = request.json
		mv     = ImdbMovie.query.filter_by(name = params['name'],director = params['director']).first()
		if not mv:
			
			try:
				genre      = json.dumps(params['genre'])
				mv = ImdbMovie(
					popularity = params['99popularity'],
        				director   = params['director'],
        				imdb_score = params['imdb_score'],
        				name       = params['name'],
        				genre      = genre,
        				#added_by   = params['user_id']
        				added_by   = user_id
				     ) 
				db.session.add(mv)
				db.session.commit() 
			except Exception as e:
				return  make_response( 'Internal Server Error' + str(e) , 500 )  
			return  make_response('Successfully Added!', 201 )  
		else:
			return make_response('Movie already exists.', 202)
		

@verify_token
@app.route("/imdb/edit" ,  methods = ['DELETE', 'POST'])
def edit_movie(user_id):
	params = request.json
	if params.get('mv_id'):
		mv     = ImdbMovie.query.get(params.get('mv_id'))
		if request.method == 'POST':
			try:
				mv.name       = params.get('name')
				mv.director   = params.get('director')
				mv.imdb_score = params.get('imdb_score')
				mv.popularity = params.get('99popularity')
				db.session.commit()
			except Exception as e:
				return  make_response( 'Internal Server Error' + str(e) , 500 )  
			return  make_response('Updated Successfully!', 201 )  

		elif request.method == 'DELETE':
			try:
				db.delete(mv)
				db.session.commit()
			except Exception as e:
				return  make_response( 'Internal Server Error' + str(e) , 500 )  
			return  make_response('Deleted Successfully!', 201 )  
	else:
		return  make_response('Updated Successfully!', 201 )  


@verify_token
@app.route("/imdb/list/" ,  methods = ['GET', 'POST'])
def movies_list():
	if request.method == 'GET':
		where = ' 1 = 1 '
		if request.args.get('name'):
			where = "name like '%{}%'".format(request.args['name'])
		if request.args.get('director'):
			where += " and director like '%{}%'".format(request.args.get('director')) 
		if request.args.get('imdb_score'):
			where += " and imdb_score={}".format(request.args.get('imdb_score')) 
		if request.args.get('99popularity'):
			where += " and popularity={}".format(request.args.get('99popularity')) 
				
		mvs     = db.session.query(ImdbMovie).filter(text(where)).all()
		movies_list = []
		for mv in mvs:
			genre = json.loads(mv.genre)
			#raise Exception(mv.genre)
			movies_list.append({'99popularity':mv.popularity , 'name':mv.name , 'genre':genre , 'director':mv.director , 'imdb_score':mv.imdb_score})
		return jsonify(movies_list) 

if __name__ == '__main__':
   app.run(debug = True)
   db.create_all()

