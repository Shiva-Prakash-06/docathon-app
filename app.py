#Final version for deployment
# --- IMPORTS ---
from flask import Flask, render_template, session, redirect, url_for, request, flash, jsonify
from utils.auth import admin_required
from utils.db import get_db_connection
import datetime

# --- APP SETUP ---
app = Flask(__name__)
app.config.from_pyfile('config.py')


# --- CONFIGURATION & HELPERS ---

# Updated button configuration with 'counts_as_ball' to enable over tracking
SPORT_BUTTON_CONFIG = {
    'default': [{'label': '+1', 'points': 1, 'type': 'Point', 'counts_as_ball': 0}],
    'Cricket Boys': [
        {'label': '+0', 'points': 0, 'type': 'Dot Ball', 'counts_as_ball': 1},
        {'label': '+1', 'points': 1, 'type': 'Run', 'counts_as_ball': 1},
        {'label': '+2', 'points': 2, 'type': 'Runs', 'counts_as_ball': 1},
        {'label': '+3', 'points': 3, 'type': 'Runs', 'counts_as_ball': 1},
        {'label': '+4', 'points': 4, 'type': 'Boundary', 'counts_as_ball': 1},
        {'label': '+6', 'points': 6, 'type': 'Boundary', 'counts_as_ball': 1},
        {'label': 'W', 'points': 0, 'type': 'Wicket', 'counts_as_ball': 1},
    ],
    'Cricket Girls': [
        {'label': '+0', 'points': 0, 'type': 'Dot Ball', 'counts_as_ball': 1},
        {'label': '+1', 'points': 1, 'type': 'Run', 'counts_as_ball': 1},
        {'label': '+2', 'points': 2, 'type': 'Runs', 'counts_as_ball': 1},
        {'label': '+3', 'points': 3, 'type': 'Runs', 'counts_as_ball': 1},
        {'label': '+4', 'points': 4, 'type': 'Boundary', 'counts_as_ball': 1},
        {'label': '+6', 'points': 6, 'type': 'Boundary', 'counts_as_ball': 1},
        {'label': 'W', 'points': 0, 'type': 'Wicket', 'counts_as_ball': 1},
    ],
    'Basketball (B)': [
        {'label': '+1', 'points': 1, 'type': 'Freethrow', 'counts_as_ball': 0},
        {'label': '+2', 'points': 2, 'type': 'Shot', 'counts_as_ball': 0},
        {'label': '+3', 'points': 3, 'type': 'Shot', 'counts_as_ball': 0},
    ],
    'Basketball (G)': [
        {'label': '+1', 'points': 1, 'type': 'Freethrow', 'counts_as_ball': 0},
        {'label': '+2', 'points': 2, 'type': 'Shot', 'counts_as_ball': 0},
        {'label': '+3', 'points': 3, 'type': 'Shot', 'counts_as_ball': 0},
    ],
}

# New helper function to calculate score, wickets, and overs for a team.
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

    # Query for the Top 3 on the leaderboard
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
            ) GROUP BY class_id
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
        )
        SELECT
            cs.class_name,
            (IFNULL(tp.tournament_points, 0) + IFNULL(pp.participation_points, 0) + IFNULL(ap.adjustment_points, 0)) AS total_points
        FROM ClassStats cs
        LEFT JOIN ParticipationPoints pp ON cs.class_id = pp.class_id
        LEFT JOIN AdjustmentPoints ap ON cs.class_id = ap.class_id
        LEFT JOIN TournamentPoints tp ON cs.class_id = tp.class_id
        ORDER BY total_points DESC, cs.wins DESC
        LIMIT 3;
    """
    top_teams = conn.execute(leaderboard_query).fetchall()

    # Query for today's matches
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
            -- 1. Calculate Wins, Losses, and Tournament Points from matches
            SELECT
                c.id AS class_id,
                c.name AS class_name,
                COUNT(m.id) AS played,
                SUM(CASE WHEN m.winner_id = c.id THEN 1 ELSE 0 END) AS wins,
                SUM(CASE WHEN m.winner_id != c.id THEN 1 ELSE 0 END) AS losses,
                SUM(CASE
                    WHEN m.winner_id = c.id AND r.round_type = 'FINAL' THEN 5 -- Winner
                    WHEN m.winner_id != c.id AND r.round_type = 'FINAL' THEN 4 -- Runner-up
                    WHEN m.winner_id != c.id AND r.round_type = 'SEMI_FINAL' THEN 3 -- Semi-finalist
                    WHEN m.winner_id != c.id AND r.round_type = 'QUARTER_FINAL' THEN 2 -- Quarter-finalist
                    ELSE 0
                END) AS tournament_points
            FROM classes c
            LEFT JOIN matches m ON (c.id = m.class1_id OR c.id = m.class2_id) AND m.status = 'COMPLETED'
            LEFT JOIN rounds r ON m.round_id = r.id
            GROUP BY c.id, c.name
        ),
        ParticipationPoints AS (
            -- 2. Calculate Participation Points (1 point per unique sport played)
            SELECT
                class_id,
                COUNT(DISTINCT sport_id) * 1 AS participation_points
            FROM (
                SELECT class1_id AS class_id, sport_id FROM matches WHERE status = 'COMPLETED'
                UNION ALL
                SELECT class2_id AS class_id, sport_id FROM matches WHERE status = 'COMPLETED'
            )
            GROUP BY class_id
        ),
        AdjustmentPoints AS (
            -- 3. Sum all manual adjustments
            SELECT
                class_id,
                SUM(points) AS adjustment_points
            FROM point_adjustments
            GROUP BY class_id
        )
        -- 4. Final Calculation and Ranking
        SELECT
            cs.class_name,
            cs.played,
            cs.wins,
            cs.losses,
            (IFNULL(cs.tournament_points, 0) + IFNULL(pp.participation_points, 0) + IFNULL(ap.adjustment_points, 0)) AS total_points
        FROM ClassStats cs
        LEFT JOIN ParticipationPoints pp ON cs.class_id = pp.class_id
        LEFT JOIN AdjustmentPoints ap ON cs.class_id = ap.class_id
        ORDER BY
            total_points DESC, -- Primary sort: total points
            cs.wins DESC;      -- Secondary sort: number of wins
    """
    
    standings = conn.execute(query).fetchall()
    conn.close()
    
    return render_template('public/leaderboard.html', standings=standings, page_title="Leaderboard")

@app.route('/matches')
def matches():
    """Displays a public list of all matches."""
    conn = get_db_connection()
    query = """
        SELECT
            m.id,
            m.status,
            m.result_details,
            m.match_time,
            s.name AS sport_name,
            r.name AS round_name,
            c1.name AS class1_name,
            c2.name AS class2_name
        FROM matches m
        JOIN sports s ON m.sport_id = s.id
        JOIN rounds r ON m.round_id = r.id
        JOIN classes c1 ON m.class1_id = c1.id
        JOIN classes c2 ON m.class2_id = c2.id
        ORDER BY m.match_time ASC
    """
    all_matches = conn.execute(query).fetchall()
    conn.close()
    
    return render_template('public/matches.html', all_matches=all_matches, page_title="Match Schedule")

@app.route('/matches/<int:match_id>')
def match_details(match_id):
    """Displays a detailed view of a single match, including its score log."""
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
        return redirect(url_for('matches'))

    # --- NEW LOGIC ---
    scores = {}
    is_cricket = 'Cricket' in match['sport_name']
    # If the match has started, calculate the detailed scores
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

@app.route('/about')
def about():
    """Renders the about us page."""
    return render_template('public/about.html', page_title="About Us")

# --- ADMIN AUTH ROUTES ---

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    """Admin login page."""
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
    """Logs the admin out."""
    session.pop('role', None)
    flash('You have been logged out.', 'info')
    return redirect(url_for('home'))

@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    """Admin dashboard."""
    return render_template('admin/dashboard.html')


# --- ADMIN MATCH MANAGEMENT ---

@app.route('/admin/matches')
@admin_required
def list_matches():
    """Lists all matches."""
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
    """Form to create a new match within a specific round."""
    conn = get_db_connection()
    
    if request.method == 'POST':
        # --- POST Logic ---
        round_id = request.form.get('round_id')
        class1_id = request.form.get('class1_id')
        class2_id = request.form.get('class2_id')
        match_time_str = request.form.get('match_time')
        
        if not all([round_id, class1_id, class2_id, match_time_str]):
            flash('All fields are required.', 'danger')
            return redirect(url_for('create_match'))

        if class1_id == class2_id:
            flash('A class cannot play against itself.', 'danger')
            return redirect(url_for('create_match'))

        # Get the sport_id from the selected round
        sport_id = conn.execute('SELECT sport_id FROM rounds WHERE id = ?', (round_id,)).fetchone()['sport_id']

        conn.execute(
            'INSERT INTO matches (sport_id, round_id, class1_id, class2_id, match_time, status) VALUES (?, ?, ?, ?, ?, ?)',
            (sport_id, round_id, class1_id, class2_id, match_time_str, 'UPCOMING')
        )
        conn.commit()
        conn.close()
        flash('Match created successfully!', 'success')
        return redirect(url_for('list_matches'))

    # --- GET Logic ---
    # Fetch rounds and their sport names, grouped for the dropdown
    rounds = conn.execute("""
        SELECT r.id, r.name, s.name as sport_name
        FROM rounds r
        JOIN sports s ON r.sport_id = s.id
        ORDER BY s.name, r.id
    """).fetchall()
    
    classes = conn.execute('SELECT * FROM classes ORDER BY name').fetchall()
    conn.close()
    
    default_time = datetime.datetime.now().strftime('%Y-%m-%dT%H:%M')
    return render_template('admin/match_form.html', rounds=rounds, classes=classes, default_time=default_time, form_title="Create New Match")

@app.route('/admin/matches/<int:match_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_match(match_id):
    """Form to edit an existing match (status, results, winner)."""
    conn = get_db_connection()
    
    if request.method == 'POST':
        status = request.form.get('status')
        result_details = request.form.get('result_details')
        winner_id = request.form.get('winner_id')
        notes = request.form.get('notes')

        if status == 'COMPLETED' and not winner_id:
            flash('You must select a winner for a completed match.', 'danger')
            return redirect(url_for('edit_match', match_id=match_id))
        
        if status != 'COMPLETED':
            winner_id = None
        
        conn.execute(
            'UPDATE matches SET status = ?, result_details = ?, winner_id = ?, notes = ? WHERE id = ?',
            (status, result_details, winner_id, notes, match_id)
        )
        conn.commit()
        conn.close()
        flash('Match updated successfully!', 'success')
        return redirect(url_for('list_matches'))

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
        
    return render_template('admin/match_form.html', match=match, form_title="Edit Match")

@app.route('/admin/matches/<int:match_id>/delete', methods=['POST'])
@admin_required
def delete_match(match_id):
    """Deletes a match from the database."""
    conn = get_db_connection()
    # Also delete related score logs
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
    
    # Get match and team info
    match = conn.execute('SELECT * FROM matches WHERE id = ?', (match_id,)).fetchone()
    
    # Determine winner and loser
    winner_id = match['class2_id'] if int(loser_id) == match['class1_id'] else match['class1_id']
    
    # Get names for the reason text
    winner_name = conn.execute('SELECT name FROM classes WHERE id = ?', (winner_id,)).fetchone()['name']
    loser_name = conn.execute('SELECT name FROM classes WHERE id = ?', (loser_id,)).fetchone()['name']
    sport_name = conn.execute('SELECT name FROM sports WHERE id = ?', (match['sport_id'],)).fetchone()['name']
    
    # 1. Update the match status and winner
    conn.execute(
        'UPDATE matches SET status = ?, winner_id = ? WHERE id = ?',
        ('COMPLETED', winner_id, match_id)
    )

    # 2. Add the -3 point penalty to the adjustments table 
    reason = f"Walkover in {sport_name} vs {winner_name}"
    conn.execute(
        'INSERT INTO point_adjustments (class_id, points, reason) VALUES (?, ?, ?)',
        (loser_id, -3, reason)
    )
    
    conn.commit()
    conn.close()
    
    flash(f"{loser_name} recorded with a walkover. -3 points applied.", 'success')
    return redirect(url_for('list_matches'))

@app.route('/admin/adjustments', methods=['GET', 'POST'])
@admin_required
def point_adjustments():
    """Page to manually add or subtract points for any class."""
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

    # GET request: Fetch data for the form and the log
    classes = conn.execute('SELECT * FROM classes ORDER BY name').fetchall()
    adjustments = conn.execute("""
        SELECT pa.points, pa.reason, pa.created_at, c.name as class_name
        FROM point_adjustments pa
        JOIN classes c ON pa.class_id = c.id
        ORDER BY pa.created_at DESC
    """).fetchall()
    
    conn.close()
    
    return render_template('admin/adjustments_form.html', classes=classes, adjustments=adjustments)

# --- ADMIN ROUND MANAGEMENT ---

@app.route('/admin/rounds')
@admin_required
def list_rounds():
    """Lists all created rounds, grouped by sport."""
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
    """Form to create a new round."""
    conn = get_db_connection() # Open connection at the start
    
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

    # --- THIS IS THE CORRECTED GET LOGIC ---
    # Fetch the list of sports for the dropdown menu
    sports = conn.execute('SELECT * FROM sports ORDER BY name').fetchall()
    conn.close()
    
    # Pass the 'sports' variable to the template
    return render_template('admin/round_form.html', sports=sports, form_title="Create New Round")

@app.route('/admin/rounds/<int:round_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_round(round_id):
    """Form to edit an existing round."""
    conn = get_db_connection()
    if request.method == 'POST':
        # This POST logic is already correct
        name = request.form.get('name')
        round_type = request.form.get('round_type')
        
        conn.execute('UPDATE rounds SET name = ?, round_type = ? WHERE id = ?', (name, round_type, round_id))
        conn.commit()
        conn.close()
        flash('Round updated successfully!', 'success')
        return redirect(url_for('list_rounds'))

    # --- THIS IS THE CORRECTED GET LOGIC ---
    round_data = conn.execute('SELECT * FROM rounds WHERE id = ?', (round_id,)).fetchone()
    
    # We now also fetch the list of sports, which was missing before.
    sports = conn.execute('SELECT * FROM sports ORDER BY name').fetchall()
    conn.close()
    
    if round_data is None:
        flash('Round not found!', 'danger')
        return redirect(url_for('list_rounds'))
        
    # We now pass both 'round' and 'sports' to the template.
    return render_template('admin/round_form.html', round=round_data, sports=sports, form_title="Edit Round")

@app.route('/admin/rounds/<int:round_id>/delete', methods=['POST'])
@admin_required
def delete_round(round_id):
    """Deletes a round. Fails if matches are attached."""
    conn = get_db_connection()
    # Check if any matches are associated with this round
    matches = conn.execute('SELECT id FROM matches WHERE round_id = ?', (round_id,)).fetchone()
    
    if matches:
        flash('Cannot delete this round because matches are already attached to it.', 'danger')
    else:
        conn.execute('DELETE FROM rounds WHERE id = ?', (round_id,))
        conn.commit()
        flash('Round deleted successfully.', 'success')
        
    conn.close()
    return redirect(url_for('list_rounds'))


# --- ADMIN LIVE SCORING ---

@app.route('/admin/matches/<int:match_id>/live')
@admin_required
def live_score_editor(match_id):
    """Renders the dedicated live scoring interface."""
    conn = get_db_connection()
    match = conn.execute("""
        SELECT m.*, s.name as sport_name, c1.name as class1_name, c2.name as class2_name
        FROM matches m
        JOIN sports s ON m.sport_id = s.id
        JOIN classes c1 ON m.class1_id = c1.id
        JOIN classes c2 ON m.class2_id = c2.id
        WHERE m.id = ?
    """, (match_id,)).fetchone()

    if match is None:
        flash('Match not found!', 'danger')
        return redirect(url_for('list_matches'))

    # Calculate current scores for both teams using the helper
    scores = {
        match['class1_id']: get_live_scores(conn, match_id, match['class1_id']),
        match['class2_id']: get_live_scores(conn, match_id, match['class2_id'])
    }
    
    buttons = SPORT_BUTTON_CONFIG.get(match['sport_name'], SPORT_BUTTON_CONFIG['default'])
    conn.close()
    
    # Check if the sport is cricket to conditionally show wickets/overs
    is_cricket = 'Cricket' in match['sport_name']
    
    return render_template('admin/live_score_form.html', match=match, scores=scores, buttons=buttons, is_cricket=is_cricket)


@app.route('/admin/matches/add-score', methods=['POST'])
@admin_required
def add_score():
    """AJAX endpoint to add a score event and return all updated stats."""
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
    conn.commit()

    # Calculate all new stats for the team using the helper
    new_stats = get_live_scores(conn, match_id, team_id)
    conn.close()

    # Return all updated stats in the JSON response
    return jsonify({
        'success': True,
        'team_id': team_id,
        'new_total': new_stats['score'],
        'new_wickets': new_stats['wickets'],
        'new_overs': new_stats['overs'],
        'new_balls': new_stats['balls']
    })

@app.route('/admin/matches/<int:match_id>/finalize', methods=['POST'])
@admin_required
def finalize_match(match_id):
    """Calculates the winner, generates a result string, and finalizes the match."""
    conn = get_db_connection()
    
    match = conn.execute('SELECT * FROM matches WHERE id = ?', (match_id,)).fetchone()
    
    # Calculate final stats for both teams
    stats1 = get_live_scores(conn, match_id, match['class1_id'])
    stats2 = get_live_scores(conn, match_id, match['class2_id'])
    
    # Determine the winner
    if stats1['score'] > stats2['score']:
        winner_id = match['class1_id']
        winner_stats = stats1
        loser_stats = stats2
    else:
        winner_id = match['class2_id']
        winner_stats = stats2
        loser_stats = stats1
        
    winner_name = conn.execute('SELECT name FROM classes WHERE id = ?', (winner_id,)).fetchone()['name']
    
    # Generate the result string
    score_diff = abs(winner_stats['score'] - loser_stats['score'])
    sport_name = conn.execute('SELECT name FROM sports WHERE id = ?', (match['sport_id'],)).fetchone()['name']
    
    result_details = f"{winner_name} won" # Default message
    if 'Cricket' in sport_name:
        result_details = f"{winner_name} won by {score_diff} runs"
    elif 'Basketball' in sport_name:
        result_details = f"{winner_name} won by {score_diff} points"
        
    # Update the match in the database
    conn.execute(
        'UPDATE matches SET status = ?, winner_id = ?, result_details = ? WHERE id = ?',
        ('COMPLETED', winner_id, result_details, match_id)
    )
    conn.commit()
    conn.close()
    
    flash(f"Match finalized successfully. {result_details}", 'success')
    return redirect(url_for('list_matches'))


# --- MAIN EXECUTION ---

#if __name__ == '__main__':
#    app.run(debug=True)