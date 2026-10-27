import os
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "heaven_youtube_style_v1"

# --- DATABASE CONFIG ---
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///heaven.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads'
db = SQLAlchemy(app)

# --- MODELS ---
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    bio = db.Column(db.String(500), default="Passionate Chef at HEAVEN")
    profile_pic = db.Column(db.String(200), default="/static/uploads/default.png")
    recipes = db.relationship('Recipe', backref='author', lazy=True)

class Recipe(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    city = db.Column(db.String(50))
    img = db.Column(db.String(500))
    ingredients = db.Column(db.Text)
    eng_method = db.Column(db.Text)
    urdu_method = db.Column(db.Text)
    category = db.Column(db.String(20))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False) # Linked to User

class CommunityPost(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50))
    message = db.Column(db.String(1000))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

# --- INITIALIZE DB & SEED DATA ---
with app.app_context():
    db.create_all()
    # 1. Create Admin User if not exists
    admin = User.query.filter_by(username='Admin').first()
    if not admin:
        admin = User(username='Admin', password='123', profile_pic='https://cdn-icons-png.flaticon.com/512/149/149071.png')
        db.session.add(admin)
        db.session.commit()

    # 2. Add Initial Recipes linked to Admin
    if not Recipe.query.first():
        data = [
            ('Sindhi Biryani', 'Karachi', 'https://images.unsplash.com/photo-1633945274405-b6c8069047b0?w=800', 'Rice, Chicken, Yogurt', 'Boil rice. Prepare curry. Steam.', 'Chawal ubalain. Salan banayein. Dam dain.', 'pakistani'),
            ('Mutton Karahi', 'Lahore', 'https://images.unsplash.com/photo-1545231027-63b3af16ee21?w=800', 'Mutton, Tomatoes, Butter', 'Fry with tomatoes and ginger.', 'Tamatar aur adrak mein bhonain.', 'pakistani'),
            ('Chicken Manchurian', 'Shanghai', 'https://images.unsplash.com/photo-1525755662778-989d0524087e?w=800', 'Chicken, Ketchup, Garlic', 'Fry chicken balls. Make sauce.', 'Chicken fry karain. Sauce banayein.', 'chinese'),
            ('Beef Bulgogi', 'Seoul', 'https://images.unsplash.com/photo-1591814468924-caf88d1232e1?w=800', 'Beef, Soy Sauce, Sugar', 'Grill sweet meat.', 'Meethay beef ko grill karain.', 'korean')
        ]
        for name, city, img, ing, eng, ur, cat in data:
            db.session.add(Recipe(name=name, city=city, img=img, ingredients=ing, eng_method=eng, urdu_method=ur, category=cat, author=admin))
        db.session.commit()

# --- ROUTES ---

@app.route('/')
def home(): return render_template('index.html')

@app.route('/recipes')
def recipes_main(): return redirect(url_for('category_page', category='pakistani'))

@app.route('/recipes/<category>')
def category_page(category):
    recipes = Recipe.query.filter_by(category=category.lower()).all()
    return render_template('category.html', category=category.lower(), recipes=recipes)

@app.route('/recipe_detail/<category>/<int:recipe_id>')
def recipe_detail(category, recipe_id):
    recipe = Recipe.query.get_or_404(recipe_id)
    ing_list = recipe.ingredients.split(',') if recipe.ingredients else []
    eng_list = [s.strip() for s in recipe.eng_method.split('.') if len(s.strip()) > 1]
    urdu_list = [s.strip() for s in (recipe.urdu_method or "").split('.') if len(s.strip()) > 1]
    return render_template('recipe_detail.html', recipe=recipe, ing_list=ing_list, eng_list=eng_list, urdu_list=urdu_list)

@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'user_id' not in session: return redirect(url_for('signin'))
    user = User.query.get(session['user_id'])
    if request.method == 'POST':
        new_r = Recipe(name=request.form['name'], city=request.form['city'], category=request.form['category'], 
                       img=request.form['img'], ingredients=request.form['ing'], 
                       eng_method=request.form['eng'], urdu_method=request.form['urdu'], author=user)
        db.session.add(new_r); db.session.commit(); flash("Recipe Published!")
    return render_template('dashboard.html', user=user, recipes=user.recipes)

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    if 'user_id' not in session: return redirect(url_for('signin'))
    user = User.query.get(session['user_id'])
    if request.method == 'POST':
        user.bio = request.form.get('bio')
        file = request.files.get('profile_file')
        if file and file.filename != '':
            filename = secure_filename(f"user_{user.id}.jpg")
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            user.profile_pic = f"/static/uploads/{filename}"
        db.session.commit(); return redirect(url_for('dashboard'))
    return render_template('settings.html', user=user)

@app.route('/signin', methods=['GET', 'POST'])
def signin():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form['username'].strip(), password=request.form['password'].strip()).first()
        if user:
            session.clear(); session['user_id'] = user.id; session['user'] = user.username
            return redirect(url_for('dashboard'))
        flash("Check details!")
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        u, p = request.form['username'].strip(), request.form['password'].strip()
        if not User.query.filter_by(username=u).first():
            new_user = User(username=u, password=p)
            db.session.add(new_user); db.session.commit()
            session['user_id'] = new_user.id; session['user'] = u
            return redirect(url_for('dashboard'))
    return render_template('signup.html')

@app.route('/logout')
def logout(): session.clear(); return redirect(url_for('home'))

@app.route('/delete_recipe/<int:id>')
def delete_recipe(id):
    recipe = Recipe.query.get(id)
    if recipe and recipe.user_id == session.get('user_id'):
        db.session.delete(recipe); db.session.commit()
    return redirect(url_for('dashboard'))

@app.route('/community', methods=['GET', 'POST'])
def community():
    if request.method == 'POST' and 'user' in session:
        db.session.add(CommunityPost(username=session['user'], message=request.form['message']))
        db.session.commit()
    posts = CommunityPost.query.order_by(CommunityPost.id.desc()).all()
    return render_template('community.html', posts=posts)

if __name__ == '__main__': app.run(debug=True)