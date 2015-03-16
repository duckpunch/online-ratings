from flask import Blueprint, render_template
from flask.ext.login import current_user
from flask.ext.security import login_required
from flask.ext.security import roles_required
from flask.ext.security import roles_accepted
from .tokengen import UUIDTokenGenerator as TokenGenerator
from .forms import AddGameServerForm
from .models import GoServer, Game, User, Player
from . import db, user_datastore
import logging

ratings = Blueprint("ratings", __name__)


@ratings.route('/')
@login_required
def home():
    return render_template('index.html')


@ratings.route('/ViewProfile')
@login_required
def viewprofile():
    if current_user.is_ratings_admin():
        games = Game.query.limit(30).all()
    else: 
        games = Game.query.filter(Game.white_id == current_user.id).all()
        games.extend(Game.query.filter(Game.black_id == current_user.id).all())
        players = Player.query.filter(Player.user_id == current_user.id).all()
    return render_template('profile.html', user=current_user, games=games, players=players)

@ratings.route('/LatestGames')
@login_required
def latestgames():
    if current_user.is_server_admin():
        games = Game.query.filter(Game.server_id == current_user.server_id).all()
    elif current_user.is_ratings_admin():
        games = Game.query.limit(30).all()
    else:
        pass
    return render_template('latestgames.html', user=current_user, games=games)

@ratings.route('/GameDetail/<game_id>')
@login_required
def gamedetail(game_id):
    game = Game.query.get(game_id)
    return render_template('gamedetail.html', user=current_user, game=game)


@ratings.route('/GoServers')
@login_required
@roles_required('ratings_admin')
def servers():
    servers = GoServer.query.limit(30).all()
    return render_template('servers.html', user=current_user, servers=servers)

@ratings.route('/GoServer/<server_id>')
@login_required
@roles_required('ratings_admin')
def server(server_id):
    server = GoServer.query.get(server_id)
    players = Player.query.filter(Player.server_id == server_id).limit(30).all()
    logging.info("Found server %s" % server)
    return render_template('server.html', user=current_user, server=server, players=players) 

@ratings.route('/Users')
@login_required
@roles_required('ratings_admin')
def users():
    users = User.query.limit(30).all()
    return render_template('users.html', user=current_user, users=users)

@ratings.route('/Players')
@login_required
@roles_accepted('ratings_admin', 'server_admin')
def players():
     #TODO: make this use bootstrap-table and load from /api/player_info
    if current_user.is_server_admin():
        #TODO: make /api/player_info fetch players for admins' server.
        pass
    if current_user.is_ratings_admin():
        players = Player.query.limit(30).all()
    return render_template('players.html', user=current_user, players=players)

@ratings.route('/Players/<player_id>')
@login_required
def player(player_id): 
    player = Player.query.get(player_id)
    games = Game.query.filter(Game.white_id == player.id).all()
    games.extend(Game.query.filter(Game.black_id == player.id).all())
    return render_template('player.html', user=current_user, player=player, games=games) 

@ratings.route('/AddGameServer', methods=['GET', 'POST'])
@login_required
@roles_required('ratings_admin')
def addgameserver():
    form = AddGameServerForm()
    gs = GoServer()
    if form.validate_on_submit():
        token = TokenGenerator()
        gs.name = form.gs_name.data
        gs.url = form.gs_url.data
        gs.token = token.create()
        db.session.add(gs)
        db.session.commit()
        return server(gs.id)
    return render_template('gameserver.html', form=form, gs=gs)

def user_registered_sighandler(app, user, confirm_token):
    '''
    Generate a token for the newly registered user.
    This signal handler is called every time a new user is registered.
    '''
    token = TokenGenerator()
    user.token = token.create()
    default_role = user_datastore.find_role('user')
    user_datastore.add_role_to_user(user, default_role)
    db.session.add(user)
    db.session.commit()
