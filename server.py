import os
from sqlalchemy import *
from sqlalchemy.pool import NullPool
from flask import Flask, request, render_template, g, redirect, Response, flash

tmpl_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
app = Flask(__name__, template_folder=tmpl_dir)
app.secret_key = b'_5#y2L"F4Q8z\n\xec]/'

DATABASE_USERNAME = "sst2161"
DATABASE_PASSWRD = "sst2161"
DATABASE_HOST = "35.212.75.104"
DATABASEURI = f"postgresql://{DATABASE_USERNAME}:{DATABASE_PASSWRD}@{DATABASE_HOST}/proj1part2"

engine = create_engine(DATABASEURI)

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
	conn.commit()


@app.before_request
def before_request():
	try:
		g.conn = engine.connect()
	except:
		print("uh oh, problem connecting to database")
		import traceback; traceback.print_exc()
		g.conn = None

@app.teardown_request
def teardown_request(exception):
	try:
		g.conn.close()
	except Exception as e:
		pass

@app.route('/')
def index():
	select_query = "SELECT name from test"
	cursor = g.conn.execute(text(select_query))
	names = []
	for result in cursor:
		names.append(result[0])
	cursor.close()
	context = dict(data = names)
	return render_template("index.html", **context)

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
    
    with engine.connect() as conn:
        email_check_query = text("""SELECT COUNT(*) FROM users WHERE email_address = :email;""")
        result = conn.execute(email_check_query, {'email': email})
        email_count = result.fetchone()[0]
        if email_count > 0:
            flash('An account with this email already exists', 'error')
            return redirect('/user')
        
        max_id_query = text("""SELECT MAX(CAST(user_id AS INT)) FROM users;""")
        result = conn.execute(max_id_query)
        max_id = result.fetchone()[0]
        if max_id is None:
            max_id = 1
        new_id = str(int(max_id) + 1).zfill(4)
        user_id = str(new_id)

        insert_query = text("""
            INSERT INTO users (user_id, first_name, last_name, email_address, curr_employment, description, date_joined, date_of_birth, city, ZIP, country)
            VALUES (:user_id, :first_name, :last_name, :email, :curr_employment, :description, CURRENT_DATE, :date_of_birth, :city, :ZIP, :country);
        """)

        conn.execute(insert_query, {'user_id': user_id, 'first_name': first_name, 'last_name': last_name, 'email': email, 'curr_employment': curr_employment, 'description': description, 'date_of_birth': date_of_birth, 'city': city, 'ZIP': ZIP, 'country': country})
        
        education = request.form.getlist('education[]')
        for edu in education:
            insert_education_query = text("""
                INSERT INTO users_education (user_id, education)
                VALUES (:user_id, :education);
            """)
            conn.execute(insert_education_query, {'user_id': user_id, 'education': edu})
            
        credentials = request.form.getlist('credential[]')
        for credential in credentials:
            insert_credentials_query = text("""
                INSERT INTO users_credentials (user_id, credentials)
                VALUES (:user_id, :credential);
            """)
            conn.execute(insert_credentials_query, {'user_id': user_id, 'credential': credential})

        conn.commit()

    flash('You finished created your profile', 'success')
    return redirect('/user')


@app.route('/post', methods=['GET', 'POST'])
def post():
    if request.method == 'POST':
        return add_post()
    else:
        return render_template("post.html")

def add_post():
    email = request.form['email']
    question_title = request.form['question']
    description = request.form['description']
    media = request.form.get('media', None)
    privacy = request.form['privacy']
    topics = request.form.getlist('topics')

    if media != "":
        if media.count(" ") > 0 or media.count(".") != 1 or not media.split(".")[1].isalpha():
            flash('Please enter a valid media file name', 'error')
            return redirect(request.referrer)
    
    max_id_query = text("""SELECT MAX(CAST(SUBSTRING(question_id, 2) AS INT)) FROM questions;""")
    with engine.connect() as conn:
        result = conn.execute(max_id_query)
        max_id = result.fetchone()[0]
        if max_id is None:
            max_id = 1
        new_id = str(int(max_id) + 1).zfill(4)
        question_id = 'q' + str(new_id)
        
        user_id_query = text("""
			SELECT user_id 
			FROM users 
			WHERE email_address = :email
		""")
        user_id = conn.execute(user_id_query, {'email': email}).scalar()
		
        if user_id is None:
            flash('Email does not exist in the database. Make an account to post a question.', 'error')
            return redirect(request.referrer)
        
        insert_query = text("""
            INSERT INTO questions (question_id, user_id, question_title, description, media, date_posted, privacy)
            VALUES (:question_id, :user_id, :question_title, :description, :media, CURRENT_DATE, :privacy)
        """)
        
        conn.execute(insert_query, {'question_id': question_id, 'user_id': user_id, 'question_title': question_title, 'description': description, 'media': media, 'privacy': privacy})
        
        insert_topic_query = text("""
            INSERT INTO topics (question_id, topic, user_id)
            VALUES (:question_id, :topic, :user_id)
        """)
        for topic in topics:
            conn.execute(insert_topic_query, {'question_id': question_id, 'topic': topic, 'user_id': user_id})
            
        conn.commit()
    
    flash('You created a new post', 'success')
    return redirect('/post')

@app.route('/search', methods=['GET'])
def search():
    search_words = request.args.get('q', '').split()
    results = {}

    with engine.connect() as conn:
        conditions = []
        if len(search_words) == 0:
            return render_template("search.html", search_results=results, search_words=search_words)
        for word in search_words:
            conditions.append(f"to_tsvector('english', q.question_title) @@ to_tsquery('{word}') or to_tsvector('english', q.description) @@ to_tsquery('{word}')")
        where_clause = "WHERE " + " OR ".join(conditions)
        
        query = text(f"""
            SELECT DISTINCT q.question_id, q.question_title, q.description AS question_description, u1.first_name AS question_first_name, u1.last_name AS question_last_name, q.date_posted AS question_date_posted, 
                   a.answer_id, a.description AS answer_description, u2.first_name AS answer_first_name, u2.last_name AS answer_last_name, a.date_posted AS answer_date_posted, 
                   r.description AS reply_description, u3.first_name AS reply_first_name, u3.last_name AS reply_last_name, r.date_posted AS reply_date_posted,
                   COALESCE((SELECT SUM(vote) FROM votes WHERE answer_id = a.answer_id), 0) AS total_votes
            FROM questions q 
            LEFT JOIN answer_to at ON q.question_id = at.question_id
            LEFT JOIN answers a ON at.answer_id = a.answer_id
            LEFT JOIN users u1 ON q.user_id = u1.user_id
            LEFT JOIN users u2 ON a.answered_by = u2.user_id
            LEFT JOIN reply_to rt ON a.answer_id = rt.answer_id
            LEFT JOIN replies r ON rt.reply_id = r.reply_id
            LEFT JOIN users u3 ON r.replied_by = u3.user_id
            {where_clause}
            ORDER BY q.date_posted DESC, total_votes DESC, a.date_posted DESC, r.date_posted DESC;
        """)
        
        result = conn.execute(query, {"word": word for word in search_words})
        for row in result.fetchall():
            question_id = row[0]
            answer_id = row[6]
            if question_id not in results:
                qlast = row[4] if row[4] else ''
                results[question_id] = {
                    'question_title': row[1],
                    'question_description': row[2],
                    'question_first_name': row[3],
                    'question_last_name': qlast,
                    'question_date_posted': row[5],
                    'answers': {}
                }
            if row[7]:
                if answer_id not in results[question_id]['answers']:
                    alast = row[9] if row[9] else ''
                    results[question_id]['answers'][answer_id] = {
                        'answer_description': row[7],
                        'answer_first_name': row[8],
                        'answer_last_name': alast,
                        'answer_date_posted': row[10],
                        'votes': row[15],
                        'replies': []
                    }
                if row[11]:
                    rlast = row[13] if row[13] else ''
                    results[question_id]['answers'][answer_id]['replies'].append({
                        'reply_description': row[11],
                        'reply_first_name': row[12],
                        'reply_last_name': rlast,
                        'reply_date_posted': row[14]
                    })
    
    return render_template("search.html", search_results=results, search_words=search_words)

@app.route('/topics', methods=['GET', 'POST'])
def topics():
    if request.method == 'POST':
        return search_by_topic()
    else:
        return render_template("topics.html", search_results={}, search_words=[])
    
def search_by_topic():
    topic = request.form.get('topic', '')
    search_results = {}
    if topic == "":
        return render_template("topics.html", search_results={}, search_words=[])

    with engine.connect() as conn:
        query = text(f"""
            SELECT DISTINCT q.question_id, q.question_title, q.description AS question_description, u1.first_name AS question_first_name, u1.last_name AS question_last_name, q.date_posted AS question_date_posted, 
                   a.answer_id, a.description AS answer_description, u2.first_name AS answer_first_name, u2.last_name AS answer_last_name, a.date_posted AS answer_date_posted, 
                   r.description AS reply_description, u3.first_name AS reply_first_name, u3.last_name AS reply_last_name, r.date_posted AS reply_date_posted,
                   COALESCE((SELECT SUM(vote) FROM votes WHERE answer_id = a.answer_id), 0) AS total_votes
            FROM questions q 
            LEFT JOIN answer_to at ON q.question_id = at.question_id
            LEFT JOIN answers a ON at.answer_id = a.answer_id
            LEFT JOIN users u1 ON q.user_id = u1.user_id
            LEFT JOIN users u2 ON a.answered_by = u2.user_id
            LEFT JOIN reply_to rt ON a.answer_id = rt.answer_id
            LEFT JOIN replies r ON rt.reply_id = r.reply_id
            LEFT JOIN users u3 ON r.replied_by = u3.user_id
            WHERE :topic = ANY(array(SELECT t.topic FROM topics t WHERE t.question_id = q.question_id))
            ORDER BY q.date_posted DESC, total_votes DESC, a.date_posted DESC, r.date_posted DESC;
        """)

        result = conn.execute(query, {'topic': topic})
        for row in result.fetchall():
            question_id = row[0]
            answer_id = row[6]
            if question_id not in search_results:
                qlast = row[4] if row[4] else ''
                search_results[question_id] = {
                    'question_title': row[1],
                    'question_description': row[2],
                    'question_first_name': row[3],
                    'question_last_name': qlast,
                    'question_date_posted': row[5],
                    'answers': {}
                }
            if row[7]:
                if answer_id not in search_results[question_id]['answers']:
                    alast = row[9] if row[9] else ''
                    search_results[question_id]['answers'][answer_id] = {
                        'answer_description': row[7],
                        'answer_first_name': row[8],
                        'answer_last_name': alast,
                        'answer_date_posted': row[10],
                        'votes': row[15],
                        'replies': []
                    }
                if row[11]:
                    rlast = row[13] if row[13] else ''
                    search_results[question_id]['answers'][answer_id]['replies'].append({
                        'reply_description': row[11],
                        'reply_first_name': row[12],
                        'reply_last_name': rlast,
                        'reply_date_posted': row[14]
                    })
    
    topic += " Questions"
    return render_template("topics.html", search_results=search_results, search_words=[topic])


@app.route('/answer', methods=['POST'])
def add_answer():
    email = request.form['email']
    description = request.form['description']
    media = request.form.get('media', None)
    question_id = request.form['question_id']

    if media != "":
        if media.count(" ") > 0 or media.count(".") != 1 or not media.split(".")[1].isalpha():
            flash('Please enter a valid media file name', 'error')
            return redirect(request.referrer)
    if email is None or email == '':
         flash('You did not input your email', 'error')
         return redirect(request.referrer)
    if description is None or description == '':
         flash('You did not write your answer', 'error')
         return redirect(request.referrer)
    
    try:
        with engine.begin() as conn:
            user_id_answerer_query = text("""
                SELECT user_id 
                FROM users 
                WHERE email_address = :email
            """)
            user_id_answerer = conn.execute(user_id_answerer_query, {'email': email}).scalar()

            if user_id_answerer is None:
                flash('Email does not exist in the database. Make an account to post an answer.', 'error')
                return redirect(request.referrer)

            user_id_questioner_query = text("""
                SELECT user_id 
                FROM questions 
                WHERE question_id = :question_id
            """)
            user_id_questioner = conn.execute(user_id_questioner_query, {'question_id': question_id}).scalar()

            max_answer_id_query = text("""
                SELECT MAX(answer_id) FROM answers
            """)
            max_answer_id = conn.execute(max_answer_id_query).scalar() or 0
            new_answer_id = str(int(max_answer_id) + 1).zfill(4)

            insert_answer_query = text("""
                INSERT INTO answers (answer_id, answered_by, description, media, date_posted) 
                VALUES (:new_answer_id, :user_id_answerer, :description, :media, CURRENT_DATE)
            """)
            conn.execute(insert_answer_query, {'new_answer_id': new_answer_id, 'user_id_answerer': user_id_answerer, 'description': description, 'media': media})

            insert_answer_to_query = text("""
                INSERT INTO answer_to (answer_id, question_id, answered_to, answerer) 
                VALUES (:new_answer_id, :question_id, :user_id_questioner, :user_id_answerer)
            """)
            conn.execute(insert_answer_to_query, {'new_answer_id': new_answer_id, 'question_id': question_id, 'user_id_questioner': user_id_questioner, 'user_id_answerer': user_id_answerer})
    
    except Exception as e:
        print("Error:", e)
        return "Error: An unexpected error occurred", 500

    flash('You have answered this question', 'success')
    return redirect(request.referrer)

@app.route('/reply', methods=['GET', 'POST'])
def add_reply():
    email = request.form['email']
    description = request.form['description']
    answer_id = request.form['answer_id']
    if email is None or email == '':
         flash('You did not input your email', 'error')
         return redirect(request.referrer)
    if description is None or description == '':
         flash('You did not write your reply', 'error')
         return redirect(request.referrer)
    
    try:
        with engine.begin() as conn:
            user_id_replier_query = text("""
                SELECT user_id 
                FROM users 
                WHERE email_address = :email
            """)
            user_id_replier = conn.execute(user_id_replier_query, {'email': email}).scalar()
            
            if user_id_replier is None:
                flash('Email does not exist in the database. Make an account to post a reply.', 'error')
                return redirect(request.referrer)

            user_id_answerer_query = text("""
                SELECT answered_by 
                FROM answers 
                WHERE answer_id = :answer_id
            """)
            user_id_answerer = conn.execute(user_id_answerer_query, {'answer_id': answer_id}).scalar()

            max_reply_id_query = text("""SELECT MAX(reply_id) FROM replies;""")
            max_reply_id = conn.execute(max_reply_id_query).scalar() or 0
            new_reply_id = str(int(max_reply_id) + 1).zfill(4)

            insert_reply_query = text("""
                INSERT INTO replies (reply_id, replied_by, description, date_posted) 
                VALUES (:new_reply_id, :user_id_replier, :description, CURRENT_DATE);
            """)
            conn.execute(insert_reply_query, {'new_reply_id': new_reply_id, 'user_id_replier': user_id_replier, 'description': description})

            insert_reply_to_query = text("""
                INSERT INTO reply_to (reply_id, answer_id, replied_to, replier) 
                VALUES (:new_reply_id, :answer_id, :user_id_answerer, :user_id_replier);
            """)
            conn.execute(insert_reply_to_query, {'new_reply_id': new_reply_id, 'answer_id': answer_id, 'user_id_answerer': user_id_answerer, 'user_id_replier': user_id_replier})
    
    except Exception as e:
        print("Error:", e)
        return "Error: An unexpected error occurred", 500

    flash('You have replied to this answer', 'success')
    return redirect(request.referrer)

@app.route('/upvote', methods=['POST'])
def add_upvote():
    email = request.form['email']
    answer_id = request.form['answer_id']
    if email is None or email == '':
         flash('You did not input your email', 'error')
         return redirect(request.referrer)
    
    try:
        with engine.begin() as conn:
            user_id_voter_query = text("""
                SELECT user_id 
                FROM users 
                WHERE email_address = :email
            """)
            user_id_voter = conn.execute(user_id_voter_query, {'email': email}).scalar()
            
            if user_id_voter is None:
                flash('Email does not exist in the database. Make an account to vote.', 'error')
                return redirect(request.referrer)
            
            existing_vote_query = text("""
                SELECT vote 
                FROM votes 
                WHERE user_id = :user_id_voter AND answer_id = :answer_id
            """)
            existing_vote = conn.execute(existing_vote_query, {'user_id_voter': user_id_voter, 'answer_id': answer_id}).scalar()
            
            if existing_vote == -1:
                flash('You have already downvoted this answer', 'error')
                return redirect(request.referrer)
            elif existing_vote == 1:
                flash('You have already upvoted this answer', 'error')
                return redirect(request.referrer)
            
            user_id_answerer_query = text("""
                SELECT answered_by 
                FROM answers 
                WHERE answer_id = :answer_id
            """)
            user_id_answerer = conn.execute(user_id_answerer_query, {'answer_id': answer_id}).scalar()
            
            insert_vote_query = text("""
                INSERT INTO votes (user_id, answer_id, creator_id, vote) 
                VALUES (:user_id_voter, :answer_id, :user_id_answerer, 1);
            """)
            conn.execute(insert_vote_query, {'user_id_voter': user_id_voter, 'answer_id': answer_id, 'user_id_answerer': user_id_answerer})
    
    except Exception as e:
        print("Error:", e)
        return "Error: An unexpected error occurred", 500

    flash('You have upvoted this post', 'success')
    return redirect(request.referrer)

@app.route('/downvote', methods=['POST'])
def add_downvote():
    email = request.form['email']
    answer_id = request.form['answer_id']
    if email is None or email == '':
         flash('You did not input your email', 'error')
         return redirect(request.referrer)
    
    try:
        with engine.begin() as conn:
            user_id_voter_query = text("""
                SELECT user_id 
                FROM users 
                WHERE email_address = :email
            """)
            user_id_voter = conn.execute(user_id_voter_query, {'email': email}).scalar()
            
            if user_id_voter is None:
                flash('Email does not exist in the database. Make an account to vote.', 'error')
                return redirect(request.referrer)
            
            existing_vote_query = text("""
                SELECT vote 
                FROM votes 
                WHERE user_id = :user_id_voter AND answer_id = :answer_id
            """)
            existing_vote = conn.execute(existing_vote_query, {'user_id_voter': user_id_voter, 'answer_id': answer_id}).scalar()
            
            if existing_vote == -1:
                flash('You have already downvoted this answer', 'error')
                return redirect(request.referrer)
            elif existing_vote == 1:
                flash('You have already upvoted this answer', 'error')
                return redirect(request.referrer)
            
            user_id_answerer_query = text("""
                SELECT answered_by 
                FROM answers 
                WHERE answer_id = :answer_id
            """)
            user_id_answerer = conn.execute(user_id_answerer_query, {'answer_id': answer_id}).scalar()
            
            insert_vote_query = text("""
                INSERT INTO votes (user_id, answer_id, creator_id, vote) 
                VALUES (:user_id_voter, :answer_id, :user_id_answerer, -1);
            """)
            conn.execute(insert_vote_query, {'user_id_voter': user_id_voter, 'answer_id': answer_id, 'user_id_answerer': user_id_answerer})
    
    except Exception as e:
        print("Error:", e)
        return "Error: An unexpected error occurred", 500

    flash('You have downvoted this post', 'success')
    return redirect(request.referrer)

@app.route('/follow', methods=['POST'])
def follow():
    email = request.form['email']
    question_id = request.form.get('question_id')
    answer_id = request.form.get('answer_id')
    reply_id = request.form.get('reply_id')
    followee_id = request.form.get('friend_id')

    if email is None or email == '':
        flash('You did not input your email', 'error')
        return redirect(request.referrer)
    try:
        with engine.begin() as conn:
            follower_id_query = text("""
                SELECT user_id 
                FROM users 
                WHERE email_address = :email
            """)
            follower_id = conn.execute(follower_id_query, {'email': email}).scalar()

            if follower_id is None:
                flash('Email does not exist in the database. Make an account to follow other users.', 'error')
                return redirect(request.referrer)

            if not followee_id:
                if question_id:
                    followee_id_query = text("""
						SELECT user_id 
						FROM questions 
						WHERE question_id = :question_id
					""")
                    followee_id = conn.execute(followee_id_query, {'question_id': question_id}).scalar()
                elif answer_id:
                    followee_id_query = text("""
						SELECT user_id 
						FROM answers 
						WHERE answer_id = :answer_id
					""")
                    followee_id = conn.execute(followee_id_query, {'answer_id': answer_id}).scalar()
                else:
                    followee_id_query = text("""
						SELECT user_id 
						FROM replies 
						WHERE reply_id = :reply_id
					""")
                    followee_id = conn.execute(followee_id_query, {'reply_id': reply_id}).scalar()

                if followee_id is None:
                    flash('Post does not exist in the database', 'error')
                    return redirect(request.referrer)
                
            if follower_id == followee_id:
                flash('You can not follow yourself', 'error')
                return redirect(request.referrer)

            check_follow_query = text("""
                SELECT *
                FROM follows 
                WHERE follower_id = :follower_id AND followee_id = :followee_id
            """)
            follow_exists = conn.execute(check_follow_query, {'follower_id': follower_id, 'followee_id': followee_id}).scalar()

            if follow_exists:
                flash('You are already following this user', 'error')
                return redirect(request.referrer)

            insert_follow_query = text("""
                INSERT INTO follows (follower_id, followee_id) 
                VALUES (:follower_id, :followee_id);
            """)
            conn.execute(insert_follow_query, {'follower_id': follower_id, 'followee_id': followee_id})

            flash('You are now following this user', 'success')
            return redirect(request.referrer)

    except Exception as e:
        flash('An error occurred while following the user', 'error')
        return redirect(request.referrer)

@app.route('/followfollower', methods=['POST'])
def followfollower():
    follower_email = request.form['follower_email']
    user_email = request.form['user_email']
    try:
        with engine.begin() as conn:
            person_to_follow_query = text("""
                SELECT user_id 
                FROM users 
                WHERE email_address = :follower_email
            """)
            person_to_follow_id = conn.execute(person_to_follow_query, {'follower_email': follower_email}).scalar()

            user_id_query = text("""
                SELECT user_id 
                FROM users 
                WHERE email_address = :user_email
            """)
            user_id = conn.execute(user_id_query, {'user_email': user_email}).scalar()
            
            if person_to_follow_id is None or user_id is None:
                flash('User to follow does not exist', 'error')
                return redirect(request.referrer)
            
            if person_to_follow_id == user_id_query:
                flash('You can not follow yourself', 'error')
                return redirect(request.referrer)
            
            follow_check_query = text("""
                SELECT 1
                FROM follows
                WHERE follower_id = :user_id AND followee_id = :person_to_unfollow_id
            """)
            follow_check_result = conn.execute(follow_check_query, {'user_id': user_id, 'person_to_unfollow_id': person_to_follow_id}).scalar()
            if follow_check_result:
                flash('You are already following this person', 'error')
                return redirect(request.referrer)

            insert_follow_query = text("""
                INSERT INTO follows (follower_id, followee_id) 
                VALUES (:follower_id, :followee_id);
            """)
            conn.execute(insert_follow_query, {'follower_id': user_id, 'followee_id': person_to_follow_id})
    
    except Exception as e:
        print("Error:", e)
        flash('An error occurred while following the person', 'error')
        return redirect(request.referrer)

    flash('You have followed this person', 'success')
    return redirect(request.referrer)

@app.route('/unfollow', methods=['POST'])
def unfollow():
    followee_email = request.form['followee_email']
    user_email = request.form['user_email']

    try:
        with engine.begin() as conn:
            person_to_unfollow_query = text("""
                SELECT user_id 
                FROM users 
                WHERE email_address = :followee_email
            """)
            person_to_unfollow_id = conn.execute(person_to_unfollow_query, {'followee_email': followee_email}).scalar()

            user_id_query = text("""
                SELECT user_id 
                FROM users 
                WHERE email_address = :user_email
            """)
            user_id = conn.execute(user_id_query, {'user_email': user_email}).scalar()

            if person_to_unfollow_id is None or user_id is None:
                flash('User to unfollow does not exist', 'error')
                return redirect(request.referrer)
            
            follow_check_query = text("""
                SELECT 1
                FROM follows
                WHERE follower_id = :user_id AND followee_id = :person_to_unfollow_id
            """)
            follow_check_result = conn.execute(follow_check_query, {'user_id': user_id, 'person_to_unfollow_id': person_to_unfollow_id}).scalar()
            if not follow_check_result:
                flash('You are not following this person', 'error')
                return redirect(request.referrer)

            unfollow_query = text("""
                DELETE FROM follows
                WHERE follower_id = :user_id AND followee_id = :person_to_unfollow_id
            """)
            conn.execute(unfollow_query, {'user_id': user_id, 'person_to_unfollow_id': person_to_unfollow_id})
    
    except Exception as e:
        print("Error:", e)
        flash('An error occurred while unfollowing the person', 'error')
        return redirect(request.referrer)

    flash('You have unfollowed this person', 'success')
    return redirect(request.referrer)

@app.route('/friends', methods=['GET'])
def friends():
    email = request.args.get('email', '')
    
    if email == "None":
         return render_template("friends.html")
    elif email == '':
        flash('You did not input your email', 'error')
        return redirect(request.referrer)
        
    with engine.begin() as conn:
        user_id_query = text("""
            SELECT user_id 
            FROM users 
            WHERE email_address = :email
        """)
        user_id = conn.execute(user_id_query, {'email': email}).scalar()

        if user_id is None:
            flash('Email does not exist in the database. Make an account to follow other users.', 'error')
            return redirect(request.referrer)

        follower_query = text("""
            SELECT u.first_name, COALESCE(u.last_name, '') AS last_name, u.email_address
            FROM users u
            JOIN follows f ON u.user_id = f.follower_id
            WHERE f.followee_id = :user_id
        """)
        followers = conn.execute(follower_query, {'user_id': user_id}).fetchall()

        following_query = text("""
            SELECT u.first_name, COALESCE(u.last_name, '') AS last_name, u.email_address
            FROM users u
            JOIN follows f ON u.user_id = f.followee_id
            WHERE f.follower_id = :user_id
        """)
        following = conn.execute(following_query, {'user_id': user_id}).fetchall()
    
    followers_text = "Followers:" if followers else ""
    following_text = "Following:" if following else ""
    return render_template("friends.html", followers=followers, following=following, user_email=email, followers_text=followers_text, following_text=following_text)

@app.route('/find_friends', methods=['GET'])
def find_friends():
    email = request.args.get('email', '')
    
    if email == "None":
         return render_template("find_friends.html")
    elif email == '':
        flash('You did not input your email', 'error')
        return redirect(request.referrer)

    with engine.begin() as conn:
        friends_query = text("""
            SELECT user_id, first_name, COALESCE(last_name, '') AS last_name
            FROM users
            WHERE email_address = :email
        """)
        friends = conn.execute(friends_query, {'email': email}).fetchall()
    return render_template("find_friends.html", friends=friends, user_email=email)

@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if request.method == 'POST':
        return find_profile()
    else:
        return render_template("profile.html", info_title="", question_title="", answer_title="", reply_title="")
    
def find_profile():
    email = request.form.get('email')
    
    if not email:
        flash('Please enter an email address', 'error')
        return redirect('/profile')
    
    with engine.connect() as conn:
        user_query = text("""
            SELECT user_id FROM users WHERE email_address = :email
        """)
        user_result = conn.execute(user_query, {'email': email})
        user_id = user_result.scalar()
        
        if not user_id:
            flash('No user found with that email address', 'error')
            return redirect('/user')
        
        user_query = text("""
            SELECT * from users where user_id = :user_id;
        """)
        user_info = conn.execute(user_query, {'user_id': user_id}).fetchall()
        
        questions_query = text("""
            SELECT * FROM questions WHERE user_id = :user_id ORDER BY date_posted DESC;
        """)
        questions = conn.execute(questions_query, {'user_id': user_id}).fetchall()
        
        answers_query = text("""
            SELECT a.*, COALESCE((SELECT SUM(vote) FROM votes WHERE answer_id = a.answer_id), 0) AS total_votes FROM answers a WHERE answered_by = :user_id ORDER BY date_posted DESC;
        """)
        answers = conn.execute(answers_query, {'user_id': user_id}).fetchall()
        
        replies_query = text("""
            SELECT * FROM replies WHERE replied_by = :user_id ORDER BY date_posted DESC;
        """)
        replies = conn.execute(replies_query, {'user_id': user_id}).fetchall()
    
    return render_template('profile.html', user_info=user_info, questions=questions, answers=answers, replies=replies, info_title="User Information", question_title="Questions", answer_title="Answers", reply_title="Replies")

@app.route('/change_info', methods=['POST'])
def change_info():
    user_id = request.form.get('user_id')
    curr_employment = request.form.get('curr_employment')
    curr_employment = curr_employment if curr_employment else None
    curr_employment = "" if curr_employment == "none" else curr_employment
    description = request.form.get('description')
    description = description if description else None
    description = "" if description == "none" else description
    city = request.form.get('city')
    city = city if city else None
    city = "" if city == "none" else city
    zip = request.form.get('ZIP')
    zip = zip if zip else None
    zip = "" if zip == "none" else zip
    country = request.form.get('country')
    country = country if country else None
    country = "" if country == "none" else country

    with engine.connect() as conn:
        update_query = text("""
            UPDATE users SET
            curr_employment = COALESCE(:curr_employment, curr_employment),
            description = COALESCE(:description, description),
            city = COALESCE(:city, city),
            zip = COALESCE(:zip, zip),
            country = COALESCE(:country, country)
            WHERE user_id = :user_id;
        """)
        conn.execute(update_query, {
            'user_id': user_id,
            'curr_employment': curr_employment,
            'description': description,
            'city': city,
            'zip': zip,
            'country': country
        })
        conn.commit()

    flash('You have changed your profile', 'success')
    return redirect('/profile')

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
