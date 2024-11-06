import psycopg2
from flask import Flask, render_template, redirect, url_for, request

app = Flask(__name__)
connect = psycopg2.connect("dbname=term user=postgres password=")
cur = connect.cursor()  # create cursor

ID = ""
or_movies = "latest"
or_reviews = "latest"
search = ""

@app.route('/')
def main():
    return render_template("pj_sign.html", msg = "")

@app.route('/sign', methods=['post'])
def sign():
    id = request.form["id"]
    password = request.form["password"]
    send = request.form["send"]

    global ID
    ID = id

    cur.execute("SELECT * FROM users;")
    result = cur.fetchall()

    if (send == "sign up"):
        for user in result:
            if (id == user[0]):
                return render_template("pj_sign.html", msg = "이미 가입되어 있는 ID입니다.")
            elif (len(id) < 1 or len(password) < 1):
                return render_template("pj_sign.html", msg = "ID와 PASSWORD는 1자리 이상으로 설정해주세요.")
            else:
                cur.execute("INSERT INTO users VALUES('{}', '{}', 'user');".format(id, password))
                cur.execute("INSERT INTO user_info VALUES('{}', null, null, NOW());".format(id))
                connect.commit()
                return render_template("pj_sign.html", msg = "가입되었습니다.")
    else:
        if (send == "sign in"):
            for user in result:
                if (id == user[0] and password == user[1]):
                    return redirect(url_for("mainpage", send="latest", whose="none", myid=id))
            else:
                return render_template("pj_sign.html", msg="가입되어 있지 않은 회원입니다. 가입부터 해주세요.")


@app.route('/mainpage', methods = ['get'])
def mainpage():
    or_type = request.args['send']
    whose = request.args['whose']

    global or_movies
    global or_reviews
    global search

    if (whose == 'or_movies'):
        or_movies = or_type
        if (or_movies == 'search'):
            search = request.args["search"]
    elif (whose == 'or_reviews'):
        or_reviews = or_type
    else:
        or_movies = "latest"
        or_reviews = "latest"

    if (or_movies == "latest"):
        cur.execute("WITH t1 AS (SELECT mid, AVG(ratings) AS ratings "
                    "FROM reviews GROUP BY mid) "
                    "SELECT title, TRUNC(ratings, 1) AS ratings, director, genre, rel_date, id "
                    "FROM movies LEFT OUTER JOIN t1 ON t1.mid=movies.id ORDER BY rel_date DESC;")
    elif (or_movies == "genre"):
        cur.execute("WITH t1 AS (SELECT mid, AVG(ratings) AS ratings "
                    "FROM reviews GROUP BY mid) "
                    "SELECT title, TRUNC(ratings, 1) AS ratings, director, genre, rel_date, id "
                    "FROM movies LEFT OUTER JOIN t1 ON t1.mid=movies.id ORDER BY genre;")
    elif (or_movies == "ratings"):
        cur.execute("WITH t1 AS (SELECT mid, AVG(ratings) AS ratings "
                    "FROM reviews GROUP BY mid) "
                    "SELECT title, TRUNC(ratings, 1) AS ratings, director, genre, rel_date, id "
                    "FROM movies LEFT OUTER JOIN t1 ON t1.mid=movies.id ORDER BY ratings DESC NULLS LAST;")
    else:
        cur.execute("WITH t1 AS (SELECT mid, AVG(ratings) AS ratings "
                    "FROM reviews GROUP BY mid) "
                    "SELECT title, TRUNC(ratings, 1) AS ratings, director, genre, rel_date, id "
                    "FROM movies LEFT OUTER JOIN t1 ON t1.mid=movies.id "
                    "WHERE title like '%{}%' OR director like '%{}%';".format(search, search))
    result_m = cur.fetchall()

    if (or_reviews == "latest"):
        cur.execute("SELECT ratings, uid, title, review, rev_time, mid "
                    "FROM reviews, movies "
                    "WHERE reviews.mid=movies.id AND "
                    "reviews.uid NOT IN (SELECT opid FROM ties WHERE id='{}' AND tie='mute') "
                    "ORDER BY rev_time DESC;".format(ID))
    elif (or_reviews == "title"):
        cur.execute("SELECT ratings, uid, title, review, rev_time, mid "
                    "FROM reviews, movies "
                    "WHERE reviews.mid=movies.id AND "
                    "reviews.uid NOT IN (SELECT opid FROM ties WHERE id='{}' AND tie='mute') "
                    "ORDER BY title;".format(ID))
    else:
        cur.execute(
            "SELECT ratings, t1.uid, title, review, rev_time, mid "
            "FROM (SELECT ratings, uid, title, review, rev_time, mid "
                    "FROM reviews, movies "
                    "WHERE reviews.mid=movies.id) t1, "
                "(SELECT users.id as uid, count(distinct ties.id) AS followers "
                "FROM ties RIGHT OUTER JOIN users ON ties.opid=users.id AND tie='follow' group by users.id) t2 "
            "WHERE t1.uid=t2.uid AND t1.uid NOT IN (SELECT opid FROM ties WHERE id='{}' AND tie='mute') "
            "ORDER BY (followers, t1.uid) DESC;".format(ID))
    result_r = cur.fetchall()

    return render_template("pj_mainpage.html", movies=result_m, reviews=result_r, myid=ID)

@app.route('/movieinfo', methods = ['post'])
def movieinfo():
    mid = request.form["movie_id"]
    update = request.form["isUpdate"]

    if (update == 'Update'):
        rating = request.form["rating"]
        review = request.form["my_review"]
        cur.execute("DELETE FROM reviews WHERE mid='{}' AND uid='{}';".format(mid, ID))
        cur.execute("INSERT INTO reviews VALUES('{}', '{}', '{}', '{}', NOW());".format(mid, ID, rating, review))
        connect.commit()

    cur.execute("WITH t1 AS (SELECT mid, AVG(ratings) AS ratings "
                "FROM reviews GROUP BY mid) "
                    "SELECT title, TRUNC(ratings, 1) AS ratings, director, genre, rel_date, id "
                    "FROM movies LEFT OUTER JOIN t1 ON t1.mid=movies.id WHERE id='{}';".format(mid))
    movie = cur.fetchall()

    cur.execute("SELECT ratings, uid, review, rev_time "
                "FROM reviews "
                "WHERE mid='{}' AND uid NOT IN (SELECT opid FROM ties WHERE id='{}' AND tie='mute');".format(mid, ID))
    reviews = cur.fetchall()

    for review in reviews:
        if review[1] == ID:
            my_review = review
            break
    else:
        my_review = ('5', ID, "", "")

    return render_template("pj_movieinfo.html", movie=movie, reviews=reviews, my_review=my_review, myid=ID)

@app.route('/userinfo', methods=["post"])
def userinfo():
    uid = request.form["uid"]
    send = request.form["send"]

    if (send == "follow"):
        cur.execute("DELETE FROM ties WHERE id='{}' AND opid='{}';".format(ID, uid))
        cur.execute("INSERT INTO ties VALUES('{}','{}','follow');".format(ID, uid))
    elif (send == "mute"):
        cur.execute("DELETE FROM ties WHERE id='{}' AND opid='{}';".format(ID, uid))
        cur.execute("INSERT INTO ties VALUES('{}','{}','mute');".format(ID, uid))
    else:
        if (send == "Del"):
            mid = request.form["mid"]
            cur.execute("DELETE FROM reviews WHERE uid='{}' AND mid='{}';".format(ID, mid))
    connect.commit()

    cur.execute("SELECT ratings, title, review, rev_time, mid "
                "FROM reviews, movies "
                "WHERE reviews.mid=movies.id AND "
                "reviews.uid='{}';".format(uid))
    reviews = cur.fetchall()

    cur.execute("SELECT id FROM ties WHERE tie='follow' AND opid='{}';".format(uid))
    followers = cur.fetchall()

    cur.execute("SELECT role FROM users WHERE id='{}';".format(uid))
    role = cur.fetchall()
    role = role[0][0]

    if (uid != ID):
        return render_template("pj_userinfo.html", uid=uid, reviews=reviews, followers=followers, role=role, myid=ID)
    else:
        if (send == "unfollow"):
            opid = request.form["opid"]
            cur.execute("DELETE FROM ties WHERE id='{}' AND opid='{}' AND tie='follow';".format(ID, opid))
        elif (send == "unmute"):
            opid = request.form["opid"]
            cur.execute("DELETE FROM ties WHERE id='{}' AND opid='{}' AND tie='mute';".format(ID, opid))
        else:
            if (send == 'Add'):
                title = request.form['add_title']
                director = request.form['add_director']
                genre = request.form['add_genre']
                rel_date = request.form["add_date"]
                cur.execute("SELECT MAX(id) FROM movies")
                mid = cur.fetchall()
                mid = mid[0][0]
                mid = str(int(mid) + 1)
                cur.execute("INSERT INTO movies VALUES('{}', '{}', '{}', '{}', '{}');".format(
                    mid, title, director, genre, rel_date
                ))
        connect.commit()

        cur.execute("SELECT opid FROM ties WHERE tie='follow' AND id='{}';".format(ID))
        followed = cur.fetchall()
        cur.execute("SELECT opid FROM ties WHERE tie='mute' AND id='{}';".format(ID))
        muted = cur.fetchall()

        return render_template("pj_mypage.html", uid=uid, reviews=reviews, followers=followers,
                               followed=followed, muted=muted, role=role, myid=ID)

if __name__ == '__main__':
    app.run()