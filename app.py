# Final version for deployment
# --- IMPORTS ---
from flask import Flask, render_template, session, redirect, url_for, request, flash, jsonify
from utils.auth import admin_required
from utils.db import get_db_connection
import datetime
import os
from werkzeug.utils import secure_filename

# --- APP SETUP ---
app = Flask(__name__)
app.config.from_pyfile('config.py')
APP_ROOT = os.path.dirname(os.path.abspath(__file__))
app.config['UPLOAD_FOLDER'] = os.path.join(APP_ROOT, 'static', 'uploads')


# --- CONFIGURATION & HELPERS ---

SPORT_BUTTON_CONFIG = {
    'default': [{'label': '+1', 'points': 1, 'type': 'Point', 'counts_as_ball': 0, 'isComplex': False}],
    'Cricket Boys': [
        {'label': '+0', 'points': 0, 'type': 'Dot Ball', 'counts_as_ball': 1, 'isComplex': False},
        {'label': '+1', 'points': 1, 'type': 'Run', 'counts_as_ball': 1, 'isComplex': False},
        {'label': '+2', 'points': 2, 'type': 'Runs', 'counts_as_ball': 1, 'isComplex': False},
        {'label': '+3', 'points': 3, 'type': 'Runs', 'counts_as_ball': 1, 'isComplex': False},
        {'label': '+4', 'points': 4, 'type': 'Boundary', 'counts_as_ball': 1, 'isComplex': False},
        {'label': '+6', 'points': 6, 'type': 'Boundary', 'counts_as_ball': 1, 'isComplex': False},
        {'label': 'Wd', 'points': 1, 'type': 'Wide', 'counts_as_ball': 0, 'isComplex': True},
        {'label': 'Nb', 'points': 1, 'type': 'No-Ball', 'counts_as_ball': 0, 'isComplex': True},
        {'label': 'W', 'points': 0, 'type': 'Wicket', 'counts_as_ball': 1, 'isComplex': True},
    ],
    'Cricket Girls': [
        {'label': '+0', 'points': 0, 'type': 'Dot Ball', 'counts_as_ball': 1, 'isComplex': False},
        {'label': '+1', 'points': 1, 'type': 'Run', 'counts_as_ball': 1, 'isComplex': False},
        {'label': '+2', 'points': 2, 'type': 'Runs', 'counts_as_ball': 1, 'isComplex': False},
        {'label': '+3', 'points': 3, 'type': 'Runs', 'counts_as_ball': 1, 'isComplex': False},
        {'label': '+4', 'points': 4, 'type': 'Boundary', 'counts_as_ball': 1, 'isComplex': False},
        {'label': '+6', 'points': 6, 'type': 'Boundary', 'counts_as_ball': 1, 'isComplex': False},
        {'label': 'Wd', 'points': 1, 'type': 'Wide', 'counts_as_ball': 0, 'isComplex': True},
        {'label': 'Nb', 'points': 1, 'type': 'No-Ball', 'counts_as_ball': 0, 'isComplex': True},
        {'label': 'W', 'points': 0, 'type': 'Wicket', 'counts_as_ball': 1, 'isComplex': True},
    ],
    'Basketball (B)': [
        {'label': '+1', 'points': 1, 'type': 'Freethrow', 'counts_as_ball': 0, 'isComplex': False},
        {'label': '+2', 'points': 2, 'type': 'Shot', 'counts_as_ball': 0, 'isComplex': False},
        {'label': '+3', 'points': 3, 'type': 'Shot', 'counts_as_ball': 0, 'isComplex': False},
    ],
    'Basketball (G)': [
        {'label': '+1', 'points': 1, 'type': 'Freethrow', 'counts_as_ball': 0, 'isComplex': False},
        {'label': '+2', 'points': 2, 'type': 'Shot', 'counts_as_ball': 0, 'isComplex': False},
        {'label': '+3', 'points': 3, 'type': 'Shot', 'counts_as_ball': 0, 'isComplex': False},
    ],
}

def get_live_scores(conn, match_id, team_id):
    """Calculates all live stats for a team."""
    score = conn.execute('SELECT SUM(points_scored) FROM score_log WHERE match_id = ? AND team_id = ?', (match_id, team_id)).fetchone()[0] or 0
    wickets = conn.execute("SELECT COUNT(*) FROM score_log WHERE match_id = ? AND team_id = ? AND event_type = 'Wicket'", (match_id, team_id)).fetchone()[0] or 0
    balls_faced = conn.execute('SELECT SUM(counts_as_ball) FROM score_log WHERE match_id = ? AND team_id = ?', (match_id, team_id)).fetchone()[0] or 0
    
    overs = balls_faced // 6
    balls = balls_faced % 6
    
    return {'score': score, 'wickets': wickets, 'overs': overs, 'balls': balls}


# --- PUBLIC ROUTES ---

@app.route('/')
def home():
    """Renders a dynamic public landing page."""
    conn = get_db_connection()

    leaderboard_query = """
        WITH ClassStats AS (
            SELECT
                c.id AS class_id, c.name AS class_name,
                SUM(CASE WHEN m.winner_id = c.id THEN 1 ELSE 0 END) AS wins
            FROM classes c
            LEFT JOIN matches m ON (c.id = m.class1_id OR c.id = m.class2_id) AND m.status = 'COMPLETED'
            GROUP BY c.id, c.name
        ),
        ParticipationPoints AS (
            SELECT class_id, COUNT(DISTINCT sport_id) * 1 AS participation_points
            FROM (
                SELECT class1_id AS class_id, sport_id FROM matches WHERE status = 'COMPLETED'
                UNION ALL
                SELECT class2_id AS class_id, sport_id FROM matches WHERE status = 'COMPLETED'
            ) t
            GROUP BY class_id
        ),
        AdjustmentPoints AS (
            SELECT class_id, SUM(points) AS adjustment_points FROM point_adjustments GROUP BY class_id
        ),
        TournamentPoints AS (
            SELECT
                c.id as class_id,
                SUM(CASE
                    WHEN m.winner_id = c.id AND r.round_type = 'FINAL' THEN 5
                    WHEN m.winner_id != c.id AND r.round_type = 'FINAL' THEN 4
                    WHEN m.winner_id != c.id AND r.round_type = 'SEMI_FINAL' THEN 3
                    WHEN m.winner_id != c.id AND r.round_type = 'QUARTER_FINAL' THEN 2
                    ELSE 0
                END) AS tournament_points
            FROM classes c
            LEFT JOIN matches m ON (c.id = m.class1_id OR c.id = m.class2_id) AND m.status = 'COMPLETED'
            LEFT JOIN rounds r ON m.round_id = r.id
            GROUP BY c.id
        ),
        WinPoints AS (
            SELECT
                winner_id as class_id,
                COUNT(id) as win_points
            FROM matches
            WHERE status = 'COMPLETED' AND result_details IS NOT NULL AND result_details != ''
            GROUP BY winner_id
        )
        SELECT
            cs.class_name,
            (IFNULL(tp.tournament_points, 0) + IFNULL(pp.participation_points, 0) + IFNULL(ap.adjustment_points, 0) + IFNULL(wp.win_points, 0)) AS total_points
        FROM ClassStats cs
        LEFT JOIN ParticipationPoints pp ON cs.class_id = pp.class_id
        LEFT JOIN AdjustmentPoints ap ON cs.class_id = ap.class_id
        LEFT JOIN TournamentPoints tp ON cs.class_id = tp.class_id
        LEFT JOIN WinPoints wp ON cs.class_id = wp.class_id
        ORDER BY total_points DESC, cs.wins DESC
        LIMIT 3;
    """
    top_teams = conn.execute(leaderboard_query).fetchall()

    today_str = datetime.date.today().strftime('%Y-%m-%d')
    todays_matches_query = """
        SELECT
            m.id, m.status, m.result_details, m.match_time, s.name AS sport_name,
            c1.name AS class1_name, c2.name AS class2_name
        FROM matches m
        JOIN sports s ON m.sport_id = s.id
        JOIN classes c1 ON m.class1_id = c1.id
        JOIN classes c2 ON m.class2_id = c2.id
        WHERE date(m.match_time) = ?
        ORDER BY m.match_time ASC
    """
    todays_matches = conn.execute(todays_matches_query, (today_str,)).fetchall()
    
    conn.close()
    
    return render_template('public/index.html', top_teams=top_teams, todays_matches=todays_matches)

@app.route('/leaderboard')
def leaderboard():
    """Calculates and displays the public leaderboard."""
    conn = get_db_connection()
    
    query = """
        WITH ClassStats AS (
            SELECT
                c.id AS class_id,
                c.name AS class_name,
                COUNT(m.id) AS played,
                SUM(CASE WHEN m.winner_id = c.id THEN 1 ELSE 0 END) AS wins,
                SUM(CASE WHEN m.winner_id != c.id THEN 1 ELSE 0 END) AS losses,
                SUM(CASE
                    WHEN m.winner_id = c.id AND r.round_type = 'FINAL' THEN 5
                    WHEN m.winner_id != c.id AND r.round_type = 'FINAL' THEN 4
                    WHEN m.winner_id != c.id AND r.round_type = 'SEMI_FINAL' THEN 3
                    WHEN m.winner_id != c.id AND r.round_type = 'QUARTER_FINAL' THEN 2
                    ELSE 0
                END) AS tournament_points
            FROM classes c
            LEFT JOIN matches m ON (c.id = m.class1_id OR c.id = m.class2_id) AND m.status = 'COMPLETED'
            LEFT JOIN rounds r ON m.round_id = r.id
            GROUP BY c.id, c.name
        ),
        ParticipationPoints AS (
            SELECT
                class_id,
                COUNT(DISTINCT sport_id) * 1 AS participation_points
            FROM (
                SELECT class1_id AS class_id, sport_id FROM matches WHERE status = 'COMPLETED'
                UNION ALL
                SELECT class2_id AS class_id, sport_id FROM matches WHERE status = 'COMPLETED'
            ) t
            GROUP BY class_id
        ),
        AdjustmentPoints AS (
            SELECT
                class_id,
                SUM(points) AS adjustment_points
            FROM point_adjustments
            GROUP BY class_id
        ),
        WinPoints AS (
            SELECT
                winner_id as class_id,
                COUNT(id) as win_points
            FROM matches
            WHERE status = 'COMPLETED' AND result_details IS NOT NULL AND result_details != ''
            GROUP BY winner_id
        )
        SELECT
            cs.class_id,
            cs.class_name,
            cs.played,
            cs.wins,
            cs.losses,
            (IFNULL(cs.tournament_points, 0) + IFNULL(pp.participation_points, 0) + IFNULL(ap.adjustment_points, 0) + IFNULL(wp.win_points, 0)) AS total_points
        FROM ClassStats cs
        LEFT JOIN ParticipationPoints pp ON cs.class_id = pp.class_id
        LEFT JOIN AdjustmentPoints ap ON cs.class_id = ap.class_id
        LEFT JOIN WinPoints wp ON cs.class_id = wp.class_id
        ORDER BY
            total_points DESC,
            cs.wins DESC;
    """
    
    standings = conn.execute(query).fetchall()
    conn.close()
    
    return render_template('public/leaderboard.html', standings=standings, page_title="Leaderboard")

@app.route('/matches')
def matches():
    """Displays a public list of all matches, with filtering."""
    conn = get_db_connection()
    
    sport_filter = request.args.get('sport_id', None)
    class_filter = request.args.get('class_id', None)
    
    query = """
        SELECT
            m.id, m.status, m.result_details, m.match_time,
            s.name AS sport_name, r.name AS round_name,
            c1.name AS class1_name, c2.name AS class2_name
        FROM matches m
        JOIN sports s ON m.sport_id = s.id
        JOIN rounds r ON m.round_id = r.id
        JOIN classes c1 ON m.class1_id = c1.id
        JOIN classes c2 ON m.class2_id = c2.id
    """
    
    conditions = []
    params = []
    if sport_filter:
        conditions.append("m.sport_id = ?")
        params.append(sport_filter)
    if class_filter:
        conditions.append("(m.class1_id = ? OR m.class2_id = ?)")
        params.extend([class_filter, class_filter])
        
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
        
    query += " ORDER BY m.match_time DESC"
    
    all_matches = conn.execute(query, params).fetchall()
    
    sports = conn.execute('SELECT id, name FROM sports ORDER BY name').fetchall()
    classes = conn.execute('SELECT id, name FROM classes ORDER BY name').fetchall()
    
    conn.close()
    
    return render_template('public/matches.html', all_matches=all_matches, 
                           sports=sports, classes=classes, 
                           page_title="Match Schedule")

@app.route('/matches/<int:match_id>')
def match_details(match_id):
    """Displays a detailed view of a single match, including its score log."""
    conn = get_db_connection()
    
    # Ensure scorecard_url is selected
    match = conn.execute("""
        SELECT m.*, s.name as sport_name, r.name as round_name, c1.name as class1_name, c2.name as class2_name
        FROM matches m
        JOIN sports s ON m.sport_id = s.id
        JOIN rounds r ON m.round_id = r.id
        JOIN classes c1 ON m.class1_id = c1.id
        JOIN classes c2 ON m.class2_id = c2.id
        WHERE m.id = ?
    """, (match_id,)).fetchone()

    if match is None:
        flash('Match not found!', 'danger')
        return redirect(url_for('matches'))

    scores = {}
    is_cricket = 'Cricket' in match['sport_name']
    if match['status'] in ('LIVE', 'COMPLETED'):
        scores = {
            match['class1_id']: get_live_scores(conn, match_id, match['class1_id']),
            match['class2_id']: get_live_scores(conn, match_id, match['class2_id'])
        }

    score_log = conn.execute("""
        SELECT sl.*, c.name as team_name
        FROM score_log sl
        JOIN classes c ON sl.team_id = c.id
        WHERE sl.match_id = ?
        ORDER BY sl.created_at DESC
    """, (match_id,)).fetchall()

    conn.close()
    
    return render_template('public/match_details.html', match=match, score_log=score_log, scores=scores, is_cricket=is_cricket, page_title="Match Details")

@app.route('/api/match-scores/<int:match_id>')
def get_match_scores_api(match_id):
    """API endpoint to get the latest scores for a match."""
    conn = get_db_connection()
    
    match = conn.execute('SELECT class1_id, class2_id FROM matches WHERE id = ?', (match_id,)).fetchone()
    if match is None:
        return jsonify({'error': 'Match not found'}), 404
        
    scores = {
        match['class1_id']: get_live_scores(conn, match_id, match['class1_id']),
        match['class2_id']: get_live_scores(conn, match_id, match['class2_id'])
    }
    conn.close()
    
    return jsonify(scores)

@app.route('/brackets')
def list_brackets():
    """Lists all sports that have at least one round to view as a bracket."""
    conn = get_db_connection()
    sports_with_rounds = conn.execute("""
        SELECT DISTINCT s.id, s.name
        FROM sports s
        JOIN rounds r ON s.id = r.sport_id
        ORDER BY s.name
    """).fetchall()
    conn.close()
    return render_template('public/list_brackets.html', sports=sports_with_rounds, page_title="Tournament Brackets")

@app.route('/brackets/<int:sport_id>')
def view_bracket(sport_id):
    """Displays the tournament bracket for a single sport."""
    conn = get_db_connection()
    
    sport = conn.execute('SELECT name FROM sports WHERE id = ?', (sport_id,)).fetchone()
    if sport is None:
        return redirect(url_for('list_brackets'))

    query = """
        SELECT
            r.name as round_name,
            m.result_details,
            c1.name as class1_name,
            c2.name as class2_name,
            w.name as winner_name
        FROM matches m
        JOIN rounds r ON m.round_id = r.id
        JOIN classes c1 ON m.class1_id = c1.id
        JOIN classes c2 ON m.class2_id = c2.id
        LEFT JOIN classes w ON m.winner_id = w.id
        WHERE m.sport_id = ?
        ORDER BY r.id, m.id
    """
    matches = conn.execute(query, (sport_id,)).fetchall()
    
    rounds = {}
    for match in matches:
        round_name = match['round_name']
        if round_name not in rounds:
            rounds[round_name] = []
        rounds[round_name].append(match)
        
    conn.close()
    
    return render_template('public/brackets.html', sport_name=sport['name'], rounds=rounds, page_title=f"{sport['name']} Bracket")

@app.route('/about')
def about():
    """Renders the about us page."""
    return render_template('public/about.html', page_title="About Us")

@app.route('/stories')
def list_stories():
    """Displays a list of all trending stories."""
    conn = get_db_connection()
    # CORRECTED: The query now selects the image_filename
    stories = conn.execute('SELECT id, title, content, author, image_filename FROM stories ORDER BY created_at DESC').fetchall()
    conn.close()
    return render_template('public/list_stories.html', stories=stories, page_title="Trending Stories")

@app.route('/stories/<int:story_id>')
def view_story(story_id):
    """Displays a single story."""
    conn = get_db_connection()
    # CORRECTED: The query now selects the image_filename
    story = conn.execute('SELECT id, title, content, author, image_filename FROM stories WHERE id = ?', (story_id,)).fetchone()
    conn.close()
    if story is None:
        return redirect(url_for('list_stories'))
    return render_template('public/view_story.html', story=story, page_title=story['title'])

@app.route('/class-log/<int:class_id>')
def class_points_log(class_id):
    """Displays a detailed points breakdown for a single class."""
    conn = get_db_connection()
    
    class_info = conn.execute('SELECT name FROM classes WHERE id = ?', (class_id,)).fetchone()
    if class_info is None:
        return redirect(url_for('leaderboard'))

    # 1. Get Tournament Points
    tournament_events = conn.execute("""
        SELECT s.name as sport_name, r.round_type,
            CASE
                WHEN m.winner_id = ? AND r.round_type = 'FINAL' THEN 5
                WHEN m.winner_id != ? AND r.round_type = 'FINAL' THEN 4
                WHEN m.winner_id != ? AND r.round_type = 'SEMI_FINAL' THEN 3
                WHEN m.winner_id != ? AND r.round_type = 'QUARTER_FINAL' THEN 2
                ELSE 0
            END AS points,
            CASE WHEN m.winner_id = ? THEN 'Won' ELSE 'Lost' END AS outcome
        FROM matches m
        JOIN rounds r ON m.round_id = r.id
        JOIN sports s ON m.sport_id = s.id
        WHERE (m.class1_id = ? OR m.class2_id = ?) AND m.status = 'COMPLETED'
          AND r.round_type IN ('FINAL', 'SEMI_FINAL', 'QUARTER_FINAL') AND points > 0
    """, (class_id, class_id, class_id, class_id, class_id, class_id, class_id)).fetchall()

    # 2. Get Participation Points
    participation_events = conn.execute("""
        SELECT DISTINCT s.name as sport_name
        FROM matches m
        JOIN sports s ON m.sport_id = s.id
        WHERE (m.class1_id = ? OR m.class2_id = ?) AND m.status = 'COMPLETED'
    """, (class_id, class_id)).fetchall()

    # 3. Get Manual Adjustments
    adjustments = conn.execute(
        'SELECT points, reason FROM point_adjustments WHERE class_id = ? ORDER BY created_at DESC', (class_id,)
    ).fetchall()

    # 4. Get Regular Win Points (+1 per win, excluding walkovers)
    win_points_events = conn.execute("""
        SELECT s.name as sport_name, c2.name as opponent_name
        FROM matches m
        JOIN sports s ON m.sport_id = s.id
        JOIN classes c2 ON m.class2_id = c2.id
        WHERE m.winner_id = ? AND m.class1_id = ? AND m.result_details IS NOT NULL AND m.result_details != ''
        UNION ALL
        SELECT s.name as sport_name, c1.name as opponent_name
        FROM matches m
        JOIN sports s ON m.sport_id = s.id
        JOIN classes c1 ON m.class1_id = c1.id
        WHERE m.winner_id = ? AND m.class2_id = ? AND m.result_details IS NOT NULL AND m.result_details != ''
    """, (class_id, class_id, class_id, class_id)).fetchall()

    conn.close()

    return render_template('public/class_points_log.html',
                           class_name=class_info['name'],
                           tournament_events=tournament_events,
                           participation_events=participation_events,
                           adjustments=adjustments,
                           win_points_events=win_points_events, # Pass new data to template
                           page_title=f"Points Log for {class_info['name']}")


# --- ADMIN AUTH ROUTES ---

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        passcode = request.form.get('passcode')
        if passcode == app.config['ADMIN_PASSCODE']:
            session['role'] = 'admin'
            flash('Login successful!', 'success')
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Incorrect passcode.', 'danger')
    return render_template('admin/login.html')

@app.route('/admin/logout')
def admin_logout():
    session.pop('role', None)
    flash('You have been logged out.', 'info')
    return redirect(url_for('home'))

@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    return render_template('admin/dashboard.html')


# --- ADMIN CONTENT MANAGEMENT ---

@app.route('/admin/stories')
@admin_required
def admin_list_stories():
    """Admin page to list and manage stories."""
    conn = get_db_connection()
    stories = conn.execute('SELECT id, title, author FROM stories ORDER BY created_at DESC').fetchall()
    conn.close()
    return render_template('admin/list_stories_admin.html', stories=stories)

@app.route('/admin/stories/new', methods=['GET', 'POST'])
@admin_required
def create_story():
    """Admin form to create a new story."""
    if request.method == 'POST':
        print("--- CREATE STORY (POST) ---")
        title = request.form.get('title')
        image_file = request.files.get('image')
        
        print(f"Title received: {title}")
        print(f"Image file object: {image_file}")

        if image_file and image_file.filename != '':
            image_filename = secure_filename(image_file.filename)
            save_path = os.path.join(app.config['UPLOAD_FOLDER'], image_filename)
            print(f"Image filename: {image_filename}")
            print(f"Attempting to save to: {save_path}")
            try:
                image_file.save(save_path)
                print("SUCCESS: File saved.")
            except Exception as e:
                print(f"ERROR saving file: {e}")
                
            # ... (the rest of the function)
        else:
            image_filename = None
            print("No image file provided.")

        # ... (rest of the function)
        content = request.form.get('content')
        author = request.form.get('author')
        conn = get_db_connection()
        conn.execute(
            'INSERT INTO stories (title, content, author, image_filename) VALUES (?, ?, ?, ?)',
            (title, content, author, image_filename)
        )
        conn.commit()
        conn.close()
        flash('Story created successfully!', 'success')
        return redirect(url_for('admin_list_stories'))
            
    return render_template('admin/story_form.html', form_title="Create New Story")

@app.route('/admin/stories/<int:story_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_story(story_id):
    """Admin form to edit a story."""
    conn = get_db_connection()
    if request.method == 'POST':
        print("--- EDIT STORY (POST) ---")
        title = request.form.get('title')
        image_file = request.files.get('image')

        print(f"Title received: {title}")
        print(f"Image file object: {image_file}")
        
        current_filename = conn.execute('SELECT image_filename FROM stories WHERE id = ?', (story_id,)).fetchone()['image_filename']
        image_filename = current_filename

        if image_file and image_file.filename != '':
            image_filename = secure_filename(image_file.filename)
            save_path = os.path.join(app.config['UPLOAD_FOLDER'], image_filename)
            print(f"Image filename: {image_filename}")
            print(f"Attempting to save to: {save_path}")
            try:
                image_file.save(save_path)
                print("SUCCESS: File saved.")
            except Exception as e:
                print(f"ERROR saving file: {e}")
        else:
            print("No new image file provided.")
        
        # ... (the rest of the function)
        content = request.form.get('content')
        author = request.form.get('author')
        conn.execute(
            'UPDATE stories SET title = ?, content = ?, author = ?, image_filename = ? WHERE id = ?',
            (title, content, author, image_filename, story_id)
        )
        conn.commit()
        conn.close()
        flash('Story updated successfully!', 'success')
        return redirect(url_for('admin_list_stories'))

    story = conn.execute('SELECT * FROM stories WHERE id = ?', (story_id,)).fetchone()
    conn.close()
    return render_template('admin/story_form.html', story=story, form_title="Edit Story")

@app.route('/admin/stories/<int:story_id>/delete', methods=['POST'])
@admin_required
def delete_story(story_id):
    """Deletes a story."""
    conn = get_db_connection()
    conn.execute('DELETE FROM stories WHERE id = ?', (story_id,))
    conn.commit()
    conn.close()
    flash('Story deleted successfully.', 'success')
    return redirect(url_for('admin_list_stories'))

@app.route('/admin/rounds')
@admin_required
def list_rounds():
    conn = get_db_connection()
    rounds = conn.execute("""
        SELECT r.id, r.name, r.round_type, s.name as sport_name
        FROM rounds r
        JOIN sports s ON r.sport_id = s.id
        ORDER BY s.name, r.id
    """).fetchall()
    conn.close()
    return render_template('admin/list_rounds.html', rounds=rounds)

@app.route('/admin/rounds/new', methods=['GET', 'POST'])
@admin_required
def create_round():
    conn = get_db_connection()
    
    if request.method == 'POST':
        sport_id = request.form.get('sport_id')
        name = request.form.get('name')
        round_type = request.form.get('round_type')

        if not all([sport_id, name, round_type]):
            flash('All fields are required.', 'danger')
            return redirect(url_for('create_round'))

        conn.execute(
            'INSERT INTO rounds (sport_id, name, round_type) VALUES (?, ?, ?)',
            (sport_id, name, round_type)
        )
        conn.commit()
        conn.close()
        flash('Round created successfully!', 'success')
        return redirect(url_for('list_rounds'))

    sports = conn.execute('SELECT * FROM sports ORDER BY name').fetchall()
    conn.close()
    
    return render_template('admin/round_form.html', sports=sports, form_title="Create New Round")

@app.route('/admin/rounds/<int:round_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_round(round_id):
    conn = get_db_connection()
    if request.method == 'POST':
        name = request.form.get('name')
        round_type = request.form.get('round_type')
        
        conn.execute('UPDATE rounds SET name = ?, round_type = ? WHERE id = ?', (name, round_type, round_id))
        conn.commit()
        conn.close()
        flash('Round updated successfully!', 'success')
        return redirect(url_for('list_rounds'))

    round_data = conn.execute('SELECT * FROM rounds WHERE id = ?', (round_id,)).fetchone()
    sports = conn.execute('SELECT * FROM sports ORDER BY name').fetchall()
    conn.close()
    
    if round_data is None:
        flash('Round not found!', 'danger')
        return redirect(url_for('list_rounds'))
        
    return render_template('admin/round_form.html', round=round_data, sports=sports, form_title="Edit Round")

@app.route('/admin/rounds/<int:round_id>/delete', methods=['POST'])
@admin_required
def delete_round(round_id):
    conn = get_db_connection()
    matches = conn.execute('SELECT id FROM matches WHERE round_id = ?', (round_id,)).fetchone()
    
    if matches:
        flash('Cannot delete this round because matches are already attached to it.', 'danger')
    else:
        conn.execute('DELETE FROM rounds WHERE id = ?', (round_id,))
        conn.commit()
        flash('Round deleted successfully.', 'success')
        
    conn.close()
    return redirect(url_for('list_rounds'))

@app.route('/admin/matches')
@admin_required
def list_matches():
    conn = get_db_connection()
    query = """
        SELECT m.id, s.name as sport_name, c1.name as class1_name, c2.name as class2_name,
               m.result_details, m.status, m.match_time
        FROM matches m
        JOIN sports s ON m.sport_id = s.id
        JOIN classes c1 ON m.class1_id = c1.id
        JOIN classes c2 ON m.class2_id = c2.id
        ORDER BY m.match_time DESC
    """
    matches = conn.execute(query).fetchall()
    conn.close()
    return render_template('admin/list_matches.html', matches=matches)

@app.route('/admin/matches/new', methods=['GET', 'POST'])
@admin_required
def create_match():
    conn = get_db_connection()
    
    if request.method == 'POST':
        round_id = request.form.get('round_id')
        class1_id = request.form.get('class1_id')
        class2_id = request.form.get('class2_id')
        match_time_str = request.form.get('match_time')
        
        if not all([round_id, class1_id, class2_id, match_time_str]):
            flash('All fields are required.', 'danger')
            return redirect(url_for('create_match'))

        if class1_id == class2_id:
            flash('A class cannot play against itself. Please select two different teams.', 'danger')
            rounds = conn.execute("SELECT r.id, r.name, s.name as sport_name FROM rounds r JOIN sports s ON r.sport_id = s.id ORDER BY s.name, r.id").fetchall()
            classes = conn.execute('SELECT * FROM classes ORDER BY name').fetchall()
            conn.close()
            default_time = datetime.datetime.now().strftime('%Y-%m-%dT%H:%M')
            return render_template('admin/match_form.html', rounds=rounds, classes=classes, default_time=default_time, form_title="Create New Match", error="Teams cannot be the same.")

        sport_id = conn.execute('SELECT sport_id FROM rounds WHERE id = ?', (round_id,)).fetchone()['sport_id']

        conn.execute(
            'INSERT INTO matches (sport_id, round_id, class1_id, class2_id, match_time, status) VALUES (?, ?, ?, ?, ?, ?)',
            (sport_id, round_id, class1_id, class2_id, match_time_str, 'UPCOMING')
        )
        conn.commit()
        conn.close()
        flash('Match created successfully!', 'success')
        return redirect(url_for('list_matches'))

    # GET Logic
    rounds = conn.execute("SELECT r.id, r.name, s.name as sport_name FROM rounds r JOIN sports s ON r.sport_id = s.id ORDER BY s.name, r.id").fetchall()
    classes = conn.execute('SELECT * FROM classes ORDER BY name').fetchall()
    conn.close()
    
    default_time = datetime.datetime.now().strftime('%Y-%m-%dT%H:%M')
    return render_template('admin/match_form.html', rounds=rounds, classes=classes, default_time=default_time, form_title="Create New Match")

@app.route('/admin/matches/<int:match_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_match(match_id):
    conn = get_db_connection()
    
    if request.method == 'POST':
        status = request.form.get('status')
        result_details = request.form.get('result_details')
        winner_id = request.form.get('winner_id')
        notes = request.form.get('notes')
        scorecard_url = request.form.get('scorecard_url')

        if status == 'COMPLETED' and not winner_id:
            flash('You must select a winner for a completed match.', 'danger')
            return redirect(url_for('edit_match', match_id=match_id))
        
        if status != 'COMPLETED':
            winner_id = None
        
        conn.execute(
            'UPDATE matches SET status = ?, winner_id = ?, notes = ?, result_details = ?, scorecard_url = ? WHERE id = ?',
            (status, winner_id, notes, result_details, scorecard_url, match_id)
        )
        conn.commit()
        conn.close()
        flash('Match updated successfully!', 'success')
        return redirect(url_for('list_matches'))

    # GET Logic
    match = conn.execute("""
        SELECT m.*, s.name as sport_name, c1.name as class1_name, c2.name as class2_name
        FROM matches m
        JOIN sports s ON m.sport_id = s.id
        JOIN classes c1 ON m.class1_id = c1.id
        JOIN classes c2 ON m.class2_id = c2.id
        WHERE m.id = ?
    """, (match_id,)).fetchone()
    
    conn.close()
    
    if match is None:
        flash('Match not found!', 'danger')
        return redirect(url_for('list_matches'))
        
    uses_live_finalizer = match['sport_name'] in SPORT_BUTTON_CONFIG and match['sport_name'] != 'default'
        
    return render_template('admin/match_form.html', match=match, form_title="Edit Match", uses_live_finalizer=uses_live_finalizer)

@app.route('/admin/matches/<int:match_id>/delete', methods=['POST'])
@admin_required
def delete_match(match_id):
    conn = get_db_connection()
    conn.execute('DELETE FROM score_log WHERE match_id = ?', (match_id,))
    conn.execute('DELETE FROM matches WHERE id = ?', (match_id,))
    conn.commit()
    conn.close()
    flash('Match has been deleted successfully.', 'success')
    return redirect(url_for('list_matches'))

@app.route('/admin/matches/<int:match_id>/walkover', methods=['POST'])
@admin_required
def declare_walkover(match_id):
    """Handles the logic for a walkover."""
    loser_id = request.form.get('loser_id')
    
    if not loser_id:
        flash('Invalid request for walkover.', 'danger')
        return redirect(url_for('list_matches'))

    conn = get_db_connection()
    
    match = conn.execute('SELECT * FROM matches WHERE id = ?', (match_id,)).fetchone()
    
    winner_id = match['class2_id'] if int(loser_id) == match['class1_id'] else match['class1_id']
    
    winner_name = conn.execute('SELECT name FROM classes WHERE id = ?', (winner_id,)).fetchone()['name']
    loser_name = conn.execute('SELECT name FROM classes WHERE id = ?', (loser_id,)).fetchone()['name']
    sport_name = conn.execute('SELECT name FROM sports WHERE id = ?', (match['sport_id'],)).fetchone()['name']
    
    # NEW: Create the result string to be displayed
    result_details = f"{winner_name} won by Walkover"
    
    # Update the match to include the new result_details
    conn.execute(
        'UPDATE matches SET status = ?, winner_id = ?, result_details = ? WHERE id = ?',
        ('COMPLETED', winner_id, result_details, match_id)
    )

    reason = f"Walkover in {sport_name} vs {winner_name}"
    conn.execute(
        'INSERT INTO point_adjustments (class_id, points, reason) VALUES (?, ?, ?)',
        (loser_id, -3, reason)
    )
    
    conn.commit()
    conn.close()
    
    flash(f"{loser_name} recorded with a walkover. -3 points applied.", 'success')
    return redirect(url_for('list_matches'))
    return redirect(url_for('list_matches'))

@app.route('/admin/adjustments', methods=['GET', 'POST'])
@admin_required
def point_adjustments():
    conn = get_db_connection()

    if request.method == 'POST':
        class_id = request.form.get('class_id')
        points = request.form.get('points')
        reason = request.form.get('reason')

        if not all([class_id, points, reason]):
            flash('All fields are required.', 'danger')
        elif not points.lstrip('-').isdigit():
            flash('Points must be a valid number.', 'danger')
        else:
            conn.execute(
                'INSERT INTO point_adjustments (class_id, points, reason) VALUES (?, ?, ?)',
                (class_id, int(points), reason)
            )
            conn.commit()
            flash('Point adjustment saved successfully!', 'success')
        
        return redirect(url_for('point_adjustments'))

    # GET request
    classes = conn.execute('SELECT * FROM classes ORDER BY name').fetchall()
    adjustments = conn.execute("""
        SELECT pa.points, pa.reason, pa.created_at, c.name as class_name
        FROM point_adjustments pa
        JOIN classes c ON pa.class_id = c.id
        ORDER BY pa.created_at DESC
    """).fetchall()
    
    conn.close()
    
    return render_template('admin/adjustments_form.html', classes=classes, adjustments=adjustments)

@app.route('/admin/announcement', methods=['GET', 'POST'])
@admin_required
def manage_announcement():
    announcement_file = 'announcement.txt'
    if request.method == 'POST':
        content = request.form.get('content')
        with open(announcement_file, 'w') as f:
            f.write(content)
        flash('Announcement updated successfully!', 'success')
        return redirect(url_for('manage_announcement'))
    
    content = ""
    if os.path.exists(announcement_file):
        with open(announcement_file, 'r') as f:
            content = f.read()
            
    return render_template('admin/announcement_form.html', content=content)

@app.route('/admin/matches/<int:match_id>/live')
@admin_required
def live_score_editor(match_id):
    conn = get_db_connection()
    match = conn.execute("""
        SELECT m.*, s.name as sport_name, r.name as round_name, c1.name as class1_name, c2.name as class2_name
        FROM matches m
        JOIN sports s ON m.sport_id = s.id
        JOIN rounds r ON m.round_id = r.id
        JOIN classes c1 ON m.class1_id = c1.id
        JOIN classes c2 ON m.class2_id = c2.id
        WHERE m.id = ?
    """, (match_id,)).fetchone()

    if match is None:
        flash('Match not found!', 'danger')
        return redirect(url_for('list_matches'))

    scores = {
        match['class1_id']: get_live_scores(conn, match_id, match['class1_id']),
        match['class2_id']: get_live_scores(conn, match_id, match['class2_id'])
    }
    
    buttons = SPORT_BUTTON_CONFIG.get(match['sport_name'], SPORT_BUTTON_CONFIG['default'])
    conn.close()
    
    is_cricket = 'Cricket' in match['sport_name']
    
    return render_template('admin/live_score_form.html', match=match, scores=scores, buttons=buttons, is_cricket=is_cricket)

@app.route('/admin/matches/add-score', methods=['POST'])
@admin_required
def add_score():
    data = request.json
    match_id = data.get('match_id')
    team_id = data.get('team_id')
    points = data.get('points')
    event_type = data.get('event_type')
    counts_as_ball = data.get('counts_as_ball')

    conn = get_db_connection()
    
    conn.execute(
        'INSERT INTO score_log (match_id, team_id, points_scored, event_type, counts_as_ball) VALUES (?, ?, ?, ?, ?)',
        (match_id, team_id, points, event_type, counts_as_ball)
    )

    if event_type == 'Run Out':
        conn.execute(
            'INSERT INTO score_log (match_id, team_id, points_scored, event_type, counts_as_ball) VALUES (?, ?, ?, ?, ?)',
            (match_id, team_id, 0, 'Wicket', 0)
        )

    conn.commit()
    new_stats = get_live_scores(conn, match_id, team_id)
    conn.close()

    return jsonify({
        'success': True,
        'team_id': team_id,
        'new_total': new_stats['score'],
        'new_wickets': new_stats['wickets'],
        'new_overs': new_stats['overs'],
        'new_balls': new_stats['balls']
    })

@app.route('/admin/matches/log-complex-event', methods=['POST'])
@admin_required
def log_complex_event():
    data = request.json
    match_id = data.get('match_id')
    team_id = data.get('team_id')
    base_event = data.get('base_event')
    extra_runs = data.get('extra_runs')

    conn = get_db_connection()
    
    conn.execute(
        'INSERT INTO score_log (match_id, team_id, points_scored, event_type, counts_as_ball) VALUES (?, ?, ?, ?, ?)',
        (match_id, team_id, base_event['points'], base_event['type'], base_event['counts_as_ball'])
    )
    
    if extra_runs['points'] > 0:
        conn.execute(
            'INSERT INTO score_log (match_id, team_id, points_scored, event_type, counts_as_ball) VALUES (?, ?, ?, ?, ?)',
            (match_id, team_id, extra_runs['points'], extra_runs['type'], extra_runs['counts_as_ball'])
        )
    conn.commit()

    new_stats = get_live_scores(conn, match_id, team_id)
    conn.close()

    return jsonify({
        'success': True, 'team_id': team_id, 'new_total': new_stats['score'],
        'new_wickets': new_stats['wickets'], 'new_overs': new_stats['overs'], 'new_balls': new_stats['balls']
    })

@app.route('/admin/matches/<int:match_id>/log-event', methods=['POST'])
@admin_required
def log_manual_event(match_id):
    """Logs a manual, non-scoring event from the HTML form."""
    # Reads from request.form to handle form-data
    team_id = request.form.get('team_id')
    event_description = request.form.get('event_description')

    if not all([team_id, event_description]):
        flash('Team and event description are required.', 'danger')
    else:
        conn = get_db_connection()
        conn.execute(
            'INSERT INTO score_log (match_id, team_id, points_scored, event_type, counts_as_ball) VALUES (?, ?, ?, ?, ?)',
            (match_id, team_id, 0, event_description, 0)
        )
        conn.commit()
        conn.close()
        flash('Event logged successfully!', 'success')
    
    return redirect(url_for('live_score_editor', match_id=match_id))

@app.route('/admin/matches/<int:match_id>/finalize', methods=['POST'])
@admin_required
def finalize_match(match_id):
    conn = get_db_connection()
    
    match = conn.execute('SELECT * FROM matches WHERE id = ?', (match_id,)).fetchone()
    
    stats1 = get_live_scores(conn, match_id, match['class1_id'])
    stats2 = get_live_scores(conn, match_id, match['class2_id'])
    
    if stats1['score'] > stats2['score']:
        winner_id = match['class1_id']
    else:
        winner_id = match['class2_id']
        
    winner_name = conn.execute('SELECT name FROM classes WHERE id = ?', (winner_id,)).fetchone()['name']
    
    result_details = f"{winner_name} won"
        
    conn.execute(
        'UPDATE matches SET status = ?, winner_id = ?, result_details = ? WHERE id = ?',
        ('COMPLETED', winner_id, result_details, match_id)
    )
    conn.commit()
    conn.close()
    
    flash(f"Match finalized successfully. {result_details}", 'success')
    return redirect(url_for('list_matches'))

@app.route('/admin/matches/<int:match_id>/undo', methods=['POST'])
@admin_required
def undo_last_event(match_id):
    conn = get_db_connection()
    
    last_event = conn.execute(
        'SELECT id FROM score_log WHERE match_id = ? ORDER BY created_at DESC, id DESC LIMIT 1',
        (match_id,)
    ).fetchone()

    if last_event:
        conn.execute('DELETE FROM score_log WHERE id = ?', (last_event['id'],))
        conn.commit()
        flash('Last event has been undone.', 'success')
    else:
        flash('No event to undo.', 'warning')
        
    conn.close()
    return redirect(url_for('live_score_editor', match_id=match_id))

# --- CONTEXT PROCESSOR ---
@app.context_processor
def inject_announcement():
    """Injects the announcement text into all templates."""
    announcement_file = 'announcement.txt'
    announcement = ""
    if os.path.exists(announcement_file):
        with open(announcement_file, 'r') as f:
            announcement = f.read().strip()
    return dict(announcement=announcement)

# --- ERROR HANDLERS ---
@app.errorhandler(404)
def handle_404(e):
    """Renders a custom 404 Not Found page."""
    return render_template('public/404.html'), 404

@app.errorhandler(500)
def handle_500(e):
    """Renders a custom 500 Internal Server Error page."""
    return render_template('public/500.html'), 500