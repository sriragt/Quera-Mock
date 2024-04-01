
"""
Columbia's COMS W4111.001 Introduction to Databases
Example Webserver
To run locally:
    python server.py
Go to http://localhost:8111 in your browser.
A debugger such as "pdb" may be helpful for debugging.
Read about it online.
"""
import os
  # accessible as a variable in index.html:
from sqlalchemy import *
from sqlalchemy.pool import NullPool
from flask import Flask, request, render_template, g, redirect, Response

tmpl_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
app = Flask(__name__, template_folder=tmpl_dir)


#
# The following is a dummy URI that does not connect to a valid database. You will need to modify it to connect to your Part 2 database in order to use the data.
#
# XXX: The URI should be in the format of: 
#
#     postgresql://USER:PASSWORD@34.73.36.248/project1
#
# For example, if you had username zy2431 and password 123123, then the following line would be:
#
#     DATABASEURI = "postgresql://zy2431:123123@34.73.36.248/project1"
#
# Modify these with your own credentials you received from TA!
DATABASE_USERNAME = "sst2161"
DATABASE_PASSWRD = "sst2161"
DATABASE_HOST = "35.212.75.104" # change to 34.28.53.86 if you used database 2 for part 2
DATABASEURI = f"postgresql://{DATABASE_USERNAME}:{DATABASE_PASSWRD}@{DATABASE_HOST}/proj1part2"


#
# This line creates a database engine that knows how to connect to the URI above.
#
engine = create_engine(DATABASEURI)

#
# Example of running queries in your database
# Note that this will probably not work if you already have a table named 'test' in your database, containing meaningful data. This is only an example showing you how to run queries in your database using SQLAlchemy.
#
with engine.connect() as conn:
	create_table_command = """
	CREATE TABLE IF NOT EXISTS test (
		id serial,
		name text
	)
	"""
	res = conn.execute(text(create_table_command))
	insert_table_command = """INSERT INTO test(name) VALUES ('grace hopper'), ('alan turing'), ('ada lovelace')"""
	res = conn.execute(text(insert_table_command))
	# you need to commit for create, insert, update queries to reflect
	conn.commit()


@app.before_request
def before_request():
	"""
	This function is run at the beginning of every web request 
	(every time you enter an address in the web browser).
	We use it to setup a database connection that can be used throughout the request.

	The variable g is globally accessible.
	"""
	try:
		g.conn = engine.connect()
	except:
		print("uh oh, problem connecting to database")
		import traceback; traceback.print_exc()
		g.conn = None

@app.teardown_request
def teardown_request(exception):
	"""
	At the end of the web request, this makes sure to close the database connection.
	If you don't, the database could run out of memory!
	"""
	try:
		g.conn.close()
	except Exception as e:
		pass


#
# @app.route is a decorator around index() that means:
#   run index() whenever the user tries to access the "/" path using a GET request
#
# If you wanted the user to go to, for example, localhost:8111/foobar/ with POST or GET then you could use:
#
#       @app.route("/foobar/", methods=["POST", "GET"])
#
# PROTIP: (the trailing / in the path is important)
# 
# see for routing: https://flask.palletsprojects.com/en/1.1.x/quickstart/#routing
# see for decorators: http://simeonfranklin.com/blog/2012/jul/1/python-decorators-in-12-steps/
#
@app.route('/')
def index():
	"""
	request is a special object that Flask provides to access web request information:

	request.method:   "GET" or "POST"
	request.form:     if the browser submitted a form, this contains the data in the form
	request.args:     dictionary of URL arguments, e.g., {a:1, b:2} for http://localhost?a=1&b=2

	See its API: https://flask.palletsprojects.com/en/1.1.x/api/#incoming-request-data
	"""

	# DEBUG: this is debugging code to see what request looks like
	print(request.args)


	#
	# example of a database query
	#
	select_query = "SELECT name from test"
	cursor = g.conn.execute(text(select_query))
	names = []
	for result in cursor:
		names.append(result[0])
	cursor.close()

	#
	# Flask uses Jinja templates, which is an extension to HTML where you can
	# pass data to a template and dynamically generate HTML based on the data
	# (you can think of it as simple PHP)
	# documentation: https://realpython.com/primer-on-jinja-templating/
	#
	# You can see an example template in templates/index.html
	#
	# context are the variables that are passed to the template.
	# for example, "data" key in the context variable defined below will be 
	# accessible as a variable in index.html:
	#
	#     # will print: [u'grace hopper', u'alan turing', u'ada lovelace']
	#     <div>{{data}}</div>
	#     
	#     # creates a <div> tag for each element in data
	#     # will print: 
	#     #
	#     #   <div>grace hopper</div>
	#     #   <div>alan turing</div>
	#     #   <div>ada lovelace</div>
	#     #
	#     {% for n in data %}
	#     <div>{{n}}</div>
	#     {% endfor %}
	#
	context = dict(data = names)


	#
	# render_template looks in the templates/ folder for files.
	# for example, the below file reads template/index.html
	#
	return render_template("index.html", **context)

#
# This is an example of a different path.  You can see it at:
# 
#     localhost:8111/another
#
# Notice that the function name is another() rather than index()
# The functions for each app.route need to have different names

@app.route('/user', methods=['GET', 'POST'])
def user():
    if request.method == 'POST':
        return add_user()
    else:
        return render_template("user.html")

def add_user():
    first_name = request.form['first_name']
    last_name = request.form['last_name']
    email = request.form['email']
    curr_employment = request.form.get('curr_employment', None)
    description = request.form.get('description', None)
    date_of_birth = request.form['date_of_birth']
    city = request.form.get('city', None)
    ZIP = request.form.get('ZIP', None)
    country = request.form.get('country', None)

    insert_query = """
        INSERT INTO user_information (first_name, last_name, email, curr_employment, description, date_of_birth, city, ZIP, country)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    with engine.connect() as conn:
        conn.execute(insert_query, (first_name, last_name, email, curr_employment, description, date_of_birth, city, ZIP, country))
        conn.commit()

    return redirect('/')

@app.route('/post', methods=['GET', 'POST'])
def post():
    if request.method == 'POST':
        return add_post()
    else:
        return render_template("post.html")

def add_post():
    question_title = request.form['question_title']
    description = request.form['description']
    media = request.form.get('media', None)
    privacy = request.form['privacy']
    
    user_id = 'user_id_here'
    date_posted = 'current_date_here'
    
    insert_query = """
        INSERT INTO questions (question_title, description, media, date_posted, privacy, user_id)
        VALUES (%s, %s, %s, %s, %s, %s)
    """
    with engine.connect() as conn:
        conn.execute(insert_query, (question_title, description, media, date_posted, privacy, user_id))
        conn.commit()

    return redirect('/')

@app.route('/search', methods=['GET'])
def search():
    search_words = request.args.get('q', '').split()
    results = {}

    with engine.connect() as conn:
        conditions = []
        if len(search_words) == 0:
            print(type(search_words))
            return render_template("search.html", search_results=results, search_words=search_words)
        for word in search_words:
            conditions.append(f"to_tsvector('english', q.question_title) @@ to_tsquery('{word}') or to_tsvector('english', q.description) @@ to_tsquery('{word}')")
        where_clause = "WHERE " + " OR ".join(conditions)
        
        query = text(f"""
            SELECT q.question_id, q.question_title, q.description AS question_description, u1.first_name AS question_first_name, u1.last_name AS question_last_name, q.date_posted AS question_date_posted, 
                   a.answer_id, a.description AS answer_description, u2.first_name AS answer_first_name, u2.last_name AS answer_last_name, a.date_posted AS answer_date_posted, 
                   r.description AS reply_description, u3.first_name AS reply_first_name, u3.last_name AS reply_last_name, r.date_posted AS reply_date_posted
            FROM questions q 
            JOIN answer_to at ON q.question_id = at.question_id
            JOIN answers a ON at.answer_id = a.answer_id
            JOIN users u1 ON q.user_id = u1.user_id
            JOIN users u2 ON a.answered_by = u2.user_id
            JOIN reply_to rt ON a.answer_id = rt.answer_id
            JOIN replies r ON rt.reply_id = r.reply_id
            JOIN users u3 ON r.replied_by = u3.user_id
            {where_clause}
            ORDER BY q.date_posted DESC, a.date_posted DESC, r.date_posted DESC;
        """)
        
        result = conn.execute(query, {"word": word for word in search_words})
        for row in result.fetchall():
            question_id = row[0]
            answer_id = row[6]
            if question_id not in results:
                results[question_id] = {
                    'question_title': row[1],
                    'question_description': row[2],
                    'question_first_name': row[3],
                    'question_last_name': row[4],
                    'question_date_posted': row[5],
                    'answers': {}
                }
            if answer_id not in results[question_id]['answers']:
                results[question_id]['answers'][answer_id] = {
                    'answer_description': row[7],
                    'answer_first_name': row[8],
                    'answer_last_name': row[9],
                    'answer_date_posted': row[10],
                    'replies': []
                }
            results[question_id]['answers'][answer_id]['replies'].append({
                'reply_description': row[11],
                'reply_first_name': row[12],
                'reply_last_name': row[13],
                'reply_date_posted': row[14]
            })

    return render_template("search.html", search_results=results, search_words=search_words)



@app.route('/login')
def login():
	abort(401)
	this_is_never_executed()


if __name__ == "__main__":
	import click

	@click.command()
	@click.option('--debug', is_flag=True)
	@click.option('--threaded', is_flag=True)
	@click.argument('HOST', default='0.0.0.0')
	@click.argument('PORT', default=8111, type=int)
	def run(debug, threaded, host, port):
		"""
		This function handles command line parameters.
		Run the server using:

			python server.py

		Show the help text using:

			python server.py --help

		"""

		HOST, PORT = host, port
		print("running on %s:%d" % (HOST, PORT))
		app.run(host=HOST, port=PORT, debug=debug, threaded=threaded)

run()
