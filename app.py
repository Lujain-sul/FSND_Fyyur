#----------------------------------------------------------------------------#
# Imports
#----------------------------------------------------------------------------#

import json
import dateutil.parser
import babel
from flask import Flask, render_template, request, Response, flash, redirect, url_for
from flask_moment import Moment
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import logging
from logging import Formatter, FileHandler
from flask_wtf import Form
from forms import *
from flask_script import Manager
from datetime import datetime
import sys
#----------------------------------------------------------------------------#
# App Config.
#----------------------------------------------------------------------------#

app = Flask(__name__)
moment = Moment(app)
manager = Manager(app) # extend flask with flask script to help in seed data
app.config.from_object('config')
db = SQLAlchemy(app)

# TODO: connect to a local postgresql database, already satisfied via config file
# instantiate migration
migrate = Migrate(app, db)

#----------------------------------------------------------------------------#
# Models.
#----------------------------------------------------------------------------#

class Venue(db.Model):
    __tablename__ = 'Venue'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    city = db.Column(db.String(120), nullable=False)
    state = db.Column(db.String(120), nullable=False)
    address = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(120))
    image_link = db.Column(db.String(500))
    facebook_link = db.Column(db.String(120))
    website_link = db.Column(db.String(120))
    seeking_talent = db.Column(db.Boolean)
    seeking_description = db.Column(db.String(500))
    shows = db.relationship('Show', backref='venue', lazy=True)
    genres = db.relationship('VenueGenres', backref='venue', lazy=True)

    # TODO: implement any missing fields, as a database migration using Flask-Migrate

class Artist(db.Model):
    __tablename__ = 'Artist'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    city = db.Column(db.String(120), nullable=False)
    state = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(120))
    # genres = db.Column(db.String(120)) many to many relation
    image_link = db.Column(db.String(500))
    facebook_link = db.Column(db.String(120))
    website_link = db.Column(db.String(120))
    seeking_venue = db.Column(db.Boolean)
    seeking_description = db.Column(db.String(500))
    shows = db.relationship('Show', backref='artist', lazy=True)
    genres = db.relationship('ArtistGenres', backref='artist', lazy=True)

    # TODO: implement any missing fields, as a database migration using Flask-Migrate

# TODO Implement Show and Artist models, and complete all model relationships and properties, as a database migration.

class Show(db.Model):
    __tablename__ = 'Show'

    id = db.Column(db.Integer, primary_key=True)
    venue_id = db.Column(db.Integer, db.ForeignKey('Venue.id'), nullable=False)
    artist_id = db.Column(db.Integer, db.ForeignKey('Artist.id'), nullable=False)
    show_date = db.Column(db.DateTime, nullable=False)

# Adjacency List Relationships at https://docs.sqlalchemy.org/en/13/orm/self_referential.html
class Lookup(db.Model):
    __tablename__ = 'Lookup'

    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(120), nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey('Lookup.id'))
    children = db.relationship('Lookup', remote_side=id, backref='parent')
    venue_genres = db.relationship('VenueGenres', backref='lookup', lazy=True)
    artist_genres = db.relationship('ArtistGenres', backref='lookup', lazy=True)

class VenueGenres(db.Model):
    __tablename__ = 'Venue_Genres'

    venue_id = db.Column(db.Integer, db.ForeignKey('Venue.id'), primary_key=True)
    genre_id = db.Column(db.Integer, db.ForeignKey('Lookup.id'), primary_key=True)

class ArtistGenres(db.Model):
    __tablename__ = 'Artist_Genres'

    artist_id = db.Column(db.Integer, db.ForeignKey('Artist.id'), primary_key=True)
    genre_id = db.Column(db.Integer, db.ForeignKey('Lookup.id'), primary_key=True)

#----------------------------------------------------------------------------#
# Filters.
#----------------------------------------------------------------------------#

def format_datetime(value, format='medium'):
  date = dateutil.parser.parse(value)
  if format == 'full':
      format="EEEE MMMM, d, y 'at' h:mma"
  elif format == 'medium':
      format="EE MM, dd, y h:mma"
  return babel.dates.format_datetime(date, format)
  
app.jinja_env.filters['datetime'] = format_datetime

#----------------------------------------------------------------------------#
# Controllers.
#----------------------------------------------------------------------------#

@app.route('/')
def index():
  return render_template('pages/home.html')


#  Venues
#  ----------------------------------------------------------------

@app.route('/venues')
def venues():
  # TODO: replace with real venues data.
  #       num_shows should be aggregated based on number of upcoming shows per venue.
  venues = db.session.query(db.func.count(Show.venue_id), Venue.id, Venue.name, Venue.city)\
                     .outerjoin(Show)\
                     .group_by(Venue.id).all()

  cities = db.session.query(Venue.city, Venue.state).distinct(Venue.city).all()

  data=[{
    "city": city.city,
    "state": city.state,
    "venues": [{
      "id": venue.id,
      "name": venue.name,
      "num_upcoming_shows": venue.count,
    } for venue in venues if venue.city == city.city]
  } for city in cities]

  return render_template('pages/venues.html', areas=data)

@app.route('/venues/search', methods=['POST'])
def search_venues():
  # TODO: implement search on artists with partial string search. Ensure it is case-insensitive.
  # seach for Hop should return "The Musical Hop".
  # search for "Music" should return "The Musical Hop" and "Park Square Live Music & Coffee"
  search_term = request.form.get('search_term', '')
  venues = Venue.query.filter(Venue.name.like('%'+ search_term +'%')).all()
  today = datetime.now()

  data = [{
    "id": venue.id, 
    "name": venue.name, 
    "num_upcoming_shows": len([show for show in venue.shows if show.show_date > today])
    } for venue in venues]

  response={
    "count": len(venues),
    "data": data
  }

  return render_template('pages/search_venues.html', results=response, search_term=request.form.get('search_term', ''))

@app.route('/venues/<int:venue_id>')
def show_venue(venue_id):
  # shows the venue page with the given venue_id
  # TODO: replace with real venue data from the venues table, using venue_id
  venue = Venue.query.get(venue_id)
  genres = [genre.lookup.description for genre in venue.genres]
  today = datetime.now()
  past_shows = [show for show in venue.shows if show.show_date < today]
  upcoming_shows = [show for show in venue.shows if show.show_date > today]

  data={
    "id": venue.id,
    "name": venue.name,
    "genres": genres,
    "address": venue.address,
    "city": venue.city,
    "state": venue.state,
    "phone": venue.phone,
    "website": venue.website_link,
    "facebook_link": venue.facebook_link,
    "seeking_talent": venue.seeking_talent,
    "seeking_description": venue.seeking_description,
    "image_link": venue.image_link,
    "past_shows": past_shows,
    "upcoming_shows": upcoming_shows,
    "past_shows_count": len(past_shows),
    "upcoming_shows_count": len(upcoming_shows),
  }

  return render_template('pages/show_venue.html', venue=data)

#  Create Venue
#  ----------------------------------------------------------------

@app.route('/venues/create', methods=['GET'])
def create_venue_form():
  form = VenueForm()
  return render_template('forms/new_venue.html', form=form)

@app.route('/venues/create', methods=['POST'])
def create_venue_submission():
  # TODO: insert form data as a new Venue record in the db, instead
  # TODO: modify data to be the data object returned from db insertion
  error = False
  form = VenueForm(request.form)
  
  if form.validate():
    try:
      name = form.name.data
      city = form.city.data
      state = form.state.data
      address = form.address.data
      phone = form.phone.data
      seeking_talent = True if form.seeking_talent.data == 'Yes' else False
      seeking_description = form.seeking_description.data
      website_link = form.website_link.data
      facebook_link = form.facebook_link.data
      image_link = form.image_link.data
      genres = form.genres.data
      venue = Venue(name=name, address=address, city=city, state=state, phone=phone, website_link=website_link, facebook_link=facebook_link, seeking_talent=seeking_talent, seeking_description=seeking_description, image_link=image_link)
      db.session.add(venue)

      for genre in genres:
        genre_id = Lookup.query.filter_by(description=genre).first().id
        venueGenres = VenueGenres(venue_id=venue.id, genre_id=genre_id)
        db.session.add(venueGenres)

      db.session.commit()

    except:
      error = True
      db.session.rollback()
      print(sys.exc_info())
    
    finally:
      db.session.close()
    
    if error:
      # TODO: on unsuccessful db insert, flash an error instead.
      flash('An error occurred. Venue ' + name + ' could not be listed.')
      # see: http://flask.pocoo.org/docs/1.0/patterns/flashing/
    else:
      # on successful db insert, flash success
      flash('Venue ' + name + ' was successfully listed!')
  
  else:
    flash('Validation error occurred: ' + ' '.join(form.errors))

  return render_template('pages/home.html')

@app.route('/venues/<venue_id>', methods=['DELETE'])
def delete_venue(venue_id):
  # TODO: Complete this endpoint for taking a venue_id, and using
  # SQLAlchemy ORM to delete a record. Handle cases where the session commit could fail.
  error = False
  
  try:
    venue = Venue.query.get(venue_id)
    name = venue.name
    venue.delete()
    db.session.commit()
  except:
    error = True
    db.session.rollback()
    print(sys.exc_info())
  finally:
    db.session.close()
  
  if error:
    # TODO: on unsuccessful db delete, flash an error instead.
    flash('An error occurred. Venue ' + name + ' could not be deleted.')
    # see: http://flask.pocoo.org/docs/1.0/patterns/flashing/
  else:
    # on successful db delete, flash success
    flash('Venue ' + name + ' was successfully deleted!')

  # BONUS CHALLENGE: Implement a button to delete a Venue on a Venue Page, have it so that
  # clicking that button delete it from the db then redirect the user to the homepage
  render_template('pages/home.html')


#  Artists
#  ----------------------------------------------------------------
@app.route('/artists')
def artists():
  # TODO: replace with real data returned from querying the database
  data = Artist.query.all()
  return render_template('pages/artists.html', artists=data)

@app.route('/artists/search', methods=['POST'])
def search_artists():
  # TODO: implement search on artists with partial string search. Ensure it is case-insensitive.
  # seach for "A" should return "Guns N Petals", "Matt Quevado", and "The Wild Sax Band".
  # search for "band" should return "The Wild Sax Band".
  search_term = request.form.get('search_term', '')
  artists = Artist.query.filter(Artist.name.ilike('%'+ search_term +'%')).all()
  today = datetime.now()

  data = [{
    "id": artist.id, 
    "name": artist.name, 
    "num_upcoming_shows": len([show for show in artist.shows if show.show_date > today])
    } for artist in artists]

  response={
    "count": len(artists),
    "data": data
  }

  return render_template('pages/search_artists.html', results=response, search_term=request.form.get('search_term', ''))

@app.route('/artists/<int:artist_id>')
def show_artist(artist_id):
  # shows the venue page with the given venue_id
  # TODO: replace with real venue data from the venues table, using venue_id
  artist = Artist.query.get(artist_id)
  genres = [genre.lookup.description for genre in artist.genres]
  today = datetime.now()
  past_shows = [show for show in artist.shows if show.show_date < today]
  upcoming_shows = [show for show in artist.shows if show.show_date > today]

  data={
    "id": artist.id,
    "name": artist.name,
    "genres": genres,
    "city": artist.city,
    "state": artist.state,
    "phone": artist.phone,
    "website": artist.website_link,
    "facebook_link": artist.facebook_link,
    "seeking_venue": artist.seeking_venue,
    "seeking_description": artist.seeking_description,
    "image_link": artist.image_link,
    "past_shows": past_shows,
    "upcoming_shows": upcoming_shows,
    "past_shows_count": len(past_shows),
    "upcoming_shows_count": len(upcoming_shows),
  }

  return render_template('pages/show_artist.html', artist=data)

#  Update
#  ----------------------------------------------------------------
@app.route('/artists/<int:artist_id>/edit', methods=['GET'])
def edit_artist(artist_id):
  form = ArtistForm()
  artist = Artist.query.get(artist_id)
  genres = [genre.lookup.description for genre in artist.genres]
  
  data={
    "id": artist.id,
    "name": artist.name,
    "genres": genres,
    "city": artist.city,
    "state": artist.state,
    "phone": artist.phone,
    "website": artist.website_link,
    "facebook_link": artist.facebook_link,
    "seeking_venue": 'Yes' if artist.seeking_venue else 'No',
    "seeking_description": artist.seeking_description,
    "image_link": artist.image_link
  }
  
  form.state.default = data["state"]
  form.seeking_venue.default = data["seeking_venue"]
  form.genres.default = data["genres"]
  form.process()
  
  # TODO: populate form with fields from artist with ID <artist_id>
  return render_template('forms/edit_artist.html', form=form, artist=data)

@app.route('/artists/<int:artist_id>/edit', methods=['POST'])
def edit_artist_submission(artist_id):
  # TODO: take values from the form submitted, and update existing
  # artist record with ID <artist_id> using the new attributes
  error = False
  form = ArtistForm(request.form)
  artist = Artist.query.get(artist_id)
  
  if form.validate():
    try:
      artist.name = form.name.data
      artist.city = form.city.data
      artist.state = form.state.data
      artist.phone = form.phone.data
      artist.seeking_venue = True if form.seeking_venue.data == 'Yes' else False
      artist.seeking_description = form.seeking_description.data
      artist.website_link = form.website_link.data
      artist.facebook_link = form.facebook_link.data
      artist.image_link = form.image_link.data
      db.session.commit()
      
      genres = form.genres.data
      # delete old genres
      ArtistGenres.query.filter_by(artist_id=artist_id).delete()
      db.session.commit()
      
      for genre in genres:
        genre_id = Lookup.query.filter_by(description=genre).first().id
        artistGenres = ArtistGenres(artist_id=artist_id, genre_id=genre_id)
        db.session.add(artistGenres)

      db.session.commit()

    except:
      error = True
      db.session.rollback()
      print(sys.exc_info())
    
    finally:
      db.session.close()
    
    if error:
      # TODO: on unsuccessful db update, flash an error instead.
      flash('An error occurred. Artist ' + form.name.data + ' could not be updated.')
      # see: http://flask.pocoo.org/docs/1.0/patterns/flashing/
    else:
      # on successful db update, flash success
      flash('Artist ' + form.name.data + ' was successfully updated!')
  
  else:
    flash('Validation error occurred: ' + ' '.join(form.errors))
  
  return redirect(url_for('show_artist', artist_id=artist_id))

@app.route('/venues/<int:venue_id>/edit', methods=['GET'])
def edit_venue(venue_id):
  form = VenueForm()
  venue = Venue.query.get(venue_id)
  genres = [genre.lookup.description for genre in venue.genres]
  
  data={
    "id": venue.id,
    "name": venue.name,
    "genres": genres,
    "address": venue.address,
    "city": venue.city,
    "state": venue.state,
    "phone": venue.phone,
    "website": venue.website_link,
    "facebook_link": venue.facebook_link,
    "seeking_talent": 'Yes' if venue.seeking_talent else 'No',
    "seeking_description": venue.seeking_description,
    "image_link": venue.image_link
  }
  
  form.state.default = data["state"]
  form.seeking_talent.default = data["seeking_talent"]
  form.genres.default = data["genres"]
  form.process()
  
  # TODO: populate form with values from venue with ID <venue_id>
  return render_template('forms/edit_venue.html', form=form, venue=data)

@app.route('/venues/<int:venue_id>/edit', methods=['POST'])
def edit_venue_submission(venue_id):
  # TODO: take values from the form submitted, and update existing
  # venue record with ID <venue_id> using the new attributes
  error = False
  form = VenueForm(request.form)
  venue = Venue.query.get(venue_id)
  
  if form.validate():
    try:
      venue.name = form.name.data
      venue.city = form.city.data
      venue.state = form.state.data
      venue.address = form.address.data
      venue.phone = form.phone.data
      venue.seeking_talent = True if form.seeking_talent.data == 'Yes' else False
      venue.seeking_description = form.seeking_description.data
      venue.website_link = form.website_link.data
      venue.facebook_link = form.facebook_link.data
      venue.image_link = form.image_link.data
      db.session.commit()
      
      genres = form.genres.data
      # delete old genres
      VenueGenres.query.filter_by(venue_id=venue_id).delete()
      db.session.commit()
      
      for genre in genres:
        genre_id = Lookup.query.filter_by(description=genre).first().id
        venueGenres = VenueGenres(venue_id=venue_id, genre_id=genre_id)
        db.session.add(venueGenres)

      db.session.commit()

    except:
      error = True
      db.session.rollback()
      print(sys.exc_info())
    
    finally:
      db.session.close()
    
    if error:
      # TODO: on unsuccessful db update, flash an error instead.
      flash('An error occurred. Venue ' + form.name.data + ' could not be updated.')
      # see: http://flask.pocoo.org/docs/1.0/patterns/flashing/
    else:
      # on successful db update, flash success
      flash('Venue ' + form.name.data + ' was successfully updated!')
  
  else:
    flash('Validation error occurred: ' + ' '.join(form.errors))
  
  return redirect(url_for('show_venue', venue_id=venue_id))

#  Create Artist
#  ----------------------------------------------------------------

@app.route('/artists/create', methods=['GET'])
def create_artist_form():
  form = ArtistForm()
  return render_template('forms/new_artist.html', form=form)

@app.route('/artists/create', methods=['POST'])
def create_artist_submission():
  # called upon submitting the new artist listing form
  # TODO: insert form data as a new Artist record in the db, instead
  # TODO: modify data to be the data object returned from db insertion
  error = False
  form = ArtistForm(request.form)
  
  if form.validate():
    try:
      name = form.name.data
      city = form.city.data
      state = form.state.data
      phone = form.phone.data
      seeking_venue = True if form.seeking_venue.data == 'Yes' else False
      seeking_description = form.seeking_description.data
      website_link = form.website_link.data
      facebook_link = form.facebook_link.data
      image_link = form.image_link.data
      genres = form.genres.data
      artist = Artist(name=name, city=city, state=state, phone=phone, website_link=website_link, facebook_link=facebook_link, seeking_venue=seeking_venue, seeking_description=seeking_description, image_link=image_link)
      db.session.add(artist)

      for genre in genres:
        genre_id = Lookup.query.filter_by(description=genre).first().id
        artistGenres = ArtistGenres(artist_id=artist.id, genre_id=genre_id)
        db.session.add(artistGenres)

      db.session.commit()

    except:
      error = True
      db.session.rollback()
      print(sys.exc_info())
    
    finally:
      db.session.close()
    
    if error:
      # TODO: on unsuccessful db insert, flash an error instead.
      flash('An error occurred. Artist ' + name + ' could not be listed.')
    else:
      # on successful db insert, flash success
      flash('Artist ' + name + ' was successfully listed!')
  
  else:
    flash('Validation error occurred: ' + ' '.join(form.errors))
  
  return render_template('pages/home.html')


#  Shows
#  ----------------------------------------------------------------

@app.route('/shows')
def shows():
  # displays list of shows at /shows
  # TODO: replace with real venues data.
  shows = Show.query.all()

  data=[{
    "venue_id": show.venue.id,
    "venue_name": show.venue.name,
    "artist_id": show.artist.id,
    "artist_name": show.artist.name,
    "artist_image_link": show.artist.image_link,
    "start_time": str(show.show_date)
  } for show in shows]

  return render_template('pages/shows.html', shows=data)

@app.route('/shows/create')
def create_shows():
  # renders form. do not touch.
  form = ShowForm()
  return render_template('forms/new_show.html', form=form)

@app.route('/shows/create', methods=['POST'])
def create_show_submission():
  # called to create new shows in the db, upon submitting new show listing form
  # TODO: insert form data as a new Show record in the db, instead
  error = False
  form = ShowForm(request.form)
  
  if form.validate():
    try:
      artist_id = form.artist_id.data
      venue_id = form.venue_id.data
      start_time = form.start_time.data
      show = Show(artist_id=artist_id, venue_id=venue_id, show_date=start_time)
      db.session.add(show)
      db.session.commit()

    except:
      error = True
      db.session.rollback()
      print(sys.exc_info())
    
    finally:
      db.session.close()
    
    if error:
      # TODO: on unsuccessful db insert, flash an error instead.
      flash('An error occurred. Show could not be listed.')
      # see: http://flask.pocoo.org/docs/1.0/patterns/flashing/
    else:
      # on successful db insert, flash success
      flash('Show was successfully listed!')
  
  else:
    flash('Validation error occurred: ' + ' '.join(form.errors))
  
  return render_template('pages/home.html')

@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def server_error(error):
    return render_template('errors/500.html'), 500

# initial seeding of db with sample data
@manager.command
def seed():
  parent = Lookup(description='Genres')
  db.session.add(parent)
  db.session.commit()

  genres = [
            ('Alternative', 'Alternative'),
            ('Blues', 'Blues'),
            ('Classical', 'Classical'),
            ('Country', 'Country'),
            ('Electronic', 'Electronic'),
            ('Folk', 'Folk'),
            ('Funk', 'Funk'),
            ('Hip-Hop', 'Hip-Hop'),
            ('Heavy Metal', 'Heavy Metal'),
            ('Instrumental', 'Instrumental'),
            ('Jazz', 'Jazz'),
            ('Musical Theatre', 'Musical Theatre'),
            ('Pop', 'Pop'),
            ('Punk', 'Punk'),
            ('R&B', 'R&B'),
            ('Reggae', 'Reggae'),
            ('Rock n Roll', 'Rock n Roll'),
            ('Soul', 'Soul'),
            ('Other', 'Other')
    ]
  lookups = []
  for genre in genres:
    lookups.append(Lookup(description=genre[0], parent_id=1))
  db.session.add_all(lookups)
  db.session.commit()

  artist1 = Artist(name='Guns N Petals', city='San Francisco', state='CA', phone='326-123-5000', website_link='https://www.gunsnpetalsband.com', facebook_link= 'https://www.facebook.com/GunsNPetals', seeking_venue=True, seeking_description='Looking for shows to perform at in the San Francisco Bay Area!', image_link='https://images.unsplash.com/photo-1549213783-8284d0336c4f?ixlib=rb-1.2.1&ixid=eyJhcHBfaWQiOjEyMDd9&auto=format&fit=crop&w=300&q=80')
  artist2 = Artist(name='Matt Quevedo', city='New York', state='NY', phone='300-400-5000', facebook_link= 'https://www.facebook.com/mattquevedo923251523', seeking_venue=False, image_link='https://images.unsplash.com/photo-1495223153807-b916f75de8c5?ixlib=rb-1.2.1&ixid=eyJhcHBfaWQiOjEyMDd9&auto=format&fit=crop&w=334&q=80')
  artist3 = Artist(name='The Wild Sax Band', city='San Francisco', state='CA', phone='432-325-5432', seeking_venue=False, seeking_description='Looking for shows to perform at in the San Francisco Bay Area!', image_link='https://images.unsplash.com/photo-1558369981-f9ca78462e61?ixlib=rb-1.2.1&ixid=eyJhcHBfaWQiOjEyMDd9&auto=format&fit=crop&w=794&q=80')
  db.session.add_all([artist1, artist2, artist3])
  db.session.commit()

  artist1genres = ArtistGenres(artist_id=1, genre_id=18)
  artist3genres = ArtistGenres(artist_id=3, genre_id=12)
  db.session.add_all([artist1genres, artist3genres])
  db.session.commit()

  venue1 = Venue(name='The Musical Hop', address='1015 Folsom Street', city='San Francisco', state='CA', phone='123-123-1234', website_link='https://www.themusicalhop.com', facebook_link='https://www.facebook.com/TheMusicalHop', seeking_talent=True, seeking_description='We are on the lookout for a local artist to play every two weeks. Please call us.', image_link='https://images.unsplash.com/photo-1543900694-133f37abaaa5?ixlib=rb-1.2.1&ixid=eyJhcHBfaWQiOjEyMDd9&auto=format&fit=crop&w=400&q=60')
  venue2 = Venue(name='The Dueling Pianos Bar', address='335 Delancey Street', city='New York', state='NY', phone='914-003-1132', website_link='https://www.theduelingpianos.com', facebook_link='https://www.facebook.com/theduelingpianos', seeking_talent=False, image_link='https://images.unsplash.com/photo-1497032205916-ac775f0649ae?ixlib=rb-1.2.1&ixid=eyJhcHBfaWQiOjEyMDd9&auto=format&fit=crop&w=750&q=80')
  venue3 = Venue(name='Park Square Live Music & Coffee', address='34 Whiskey Moore Ave', city='San Francisco', state='CA', phone='415-000-1234', website_link='https://www.parksquarelivemusicandcoffee.com', facebook_link='https://www.facebook.com/ParkSquareLiveMusicAndCoffee', seeking_talent=False, image_link='https://images.unsplash.com/photo-1485686531765-ba63b07845a7?ixlib=rb-1.2.1&ixid=eyJhcHBfaWQiOjEyMDd9&auto=format&fit=crop&w=747&q=80')
  db.session.add_all([venue1, venue2, venue3])
  db.session.commit()

  genre1 = VenueGenres(venue_id=1, genre_id=12)
  genre2 = VenueGenres(venue_id=1, genre_id=17)
  genre3 = VenueGenres(venue_id=1, genre_id=4)
  genre4 = VenueGenres(venue_id=1, genre_id=7)
  genre5 = VenueGenres(venue_id=2, genre_id=4)
  genre6 = VenueGenres(venue_id=2, genre_id=16)
  genre7 = VenueGenres(venue_id=2, genre_id=9)
  genre8 = VenueGenres(venue_id=3, genre_id=18)
  genre9 = VenueGenres(venue_id=3, genre_id=12)
  genre10 = VenueGenres(venue_id=3, genre_id=4)
  genre11 = VenueGenres(venue_id=3, genre_id=7)
  db.session.add_all([genre1, genre2, genre3, genre4, genre5, genre6, genre7, genre8, genre9, genre10, genre11])
  db.session.commit()

  show1 = Show(venue_id=1, artist_id=1, show_date="2019-05-21T21:30:00.000Z")
  show2 = Show(venue_id=3, artist_id=2, show_date="2019-06-15T23:00:00.000Z")
  show3 = Show(venue_id=3, artist_id=3, show_date="2035-04-01T20:00:00.000Z")
  show4 = Show(venue_id=3, artist_id=3, show_date="2035-04-08T20:00:00.000Z")
  show5 = Show(venue_id=3, artist_id=3, show_date="2035-04-15T20:00:00.000Z")
  db.session.add_all([show1, show2, show3, show4, show5])
  db.session.commit()

if not app.debug:
    file_handler = FileHandler('error.log')
    file_handler.setFormatter(
        Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
    )
    app.logger.setLevel(logging.INFO)
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.info('errors')

#----------------------------------------------------------------------------#
# Launch.
#----------------------------------------------------------------------------#

# Default port:
if __name__ == '__main__':
  app.run() # replace it with below line for db seeding
  # manager.run() 

# Or specify port manually:
'''
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
'''
