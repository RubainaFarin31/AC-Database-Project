import sqlite3
import csv
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify

# Initialize Flask app
app = Flask(__name__)
app.secret_key = b'_5#y2L"F4Q8z\n\xec]/'

# Function to create the database if it doesn't exist
def create_database():
    conn = sqlite3.connect('chemistry_inventory.db')
    cursor = conn.cursor()

    cursor.execute('''CREATE TABLE IF NOT EXISTS Users (
                        username TEXT PRIMARY KEY,
                        password TEXT
                      )''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS Chemicals (
                        CatalogueNumber TEXT PRIMARY KEY,
                        CASNumber TEXT,
                        Location TEXT,
                        Structure TEXT,
                        MolecularWeight REAL,
                        Quantity INTEGER,
                        Barcode TEXT
                      )''')
    
    conn.commit()
    conn.close()

# Create the database before running the application
create_database()

# Upload CSV file
@app.route('/upload_csv', methods=['POST'])
def upload_csv():
    if 'username' in session:
        # Check if a file was uploaded
        if 'file' not in request.files:
            flash('No file part', 'error')
            return redirect(request.url)
        
        file = request.files['file']
        
        # Check if the file has a filename
        if file.filename == '':
            flash('No selected file', 'error')
            return redirect(request.url)
        
        if file:
            try:
                # Read the CSV file
                csv_data = file.read().decode('utf-8').splitlines()
                
                # Parse CSV data, skipping the first row (header row)
                chemicals = []
                for index, row in enumerate(csv.reader(csv_data)):
                    if index == 0:  # Skip the first row (header row)
                        continue
                    if row:  # Check if row is not empty
                        chemicals.append(tuple(row))
                
                # Insert parsed data into the database
                conn = sqlite3.connect('chemistry_inventory.db')
                cursor = conn.cursor()
                
                cursor.executemany('''INSERT OR REPLACE INTO Chemicals 
                                      (CatalogueNumber, CASNumber, Location, Structure, MolecularWeight, Quantity, Barcode)
                                      VALUES (?, ?, ?, ?, ?, ?, ?)''', chemicals)
                
                conn.commit()
                conn.close()
                
                flash('Chemicals added successfully from CSV file!', 'success')
                return redirect(url_for('index'))  # Redirect to the homepage after adding chemicals
            
            except Exception as e:
                flash(f'Error uploading CSV file: {str(e)}', 'error')
                app.logger.error(f'Error uploading CSV file: {str(e)}')
                return redirect(url_for('index'))  # Redirect to the homepage on error
        
    else:
        return redirect(url_for('login'))


@app.route('/')
def index():
    if 'username' in session:
        conn = sqlite3.connect('chemistry_inventory.db')
        cursor = conn.cursor()
        cursor.execute('''SELECT * FROM Chemicals''')
        chemicals = cursor.fetchall()
        conn.close()
        return render_template('index.html', chemicals=chemicals)
    else:
        return redirect(url_for('login'))  # Redirect to the login page if not logged in

@app.route('/search')
def search():
    query = request.args.get('query')
    conn = sqlite3.connect('chemistry_inventory.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Chemicals WHERE CatalogueNumber LIKE ? OR CASNumber LIKE ? OR Location LIKE ? OR Structure LIKE ? OR Barcode LIKE ?", ('%'+query+'%', '%'+query+'%', '%'+query+'%', '%'+query+'%', '%'+query+'%'))
    chemicals = cursor.fetchall()
    conn.close()
    return jsonify(chemicals)

@app.route('/add', methods=['GET', 'POST'])
def add_chemical():
    if 'username' in session:
        if request.method == 'POST':
            catalogue_number = request.form['catalogue_number']
            cas_number = request.form['cas_number']
            location = request.form['location']
            structure = request.form['structure']
            molecular_weight = request.form['molecular_weight']
            quantity = request.form['quantity']
            barcode = request.form['barcode']
            
            conn = sqlite3.connect('chemistry_inventory.db')
            cursor = conn.cursor()
            
            # Check if the chemical already exists
            cursor.execute('''SELECT * FROM Chemicals WHERE CatalogueNumber = ?''', (catalogue_number,))
            existing_chemical = cursor.fetchone()
            if existing_chemical:
                flash(f'Chemical with Catalogue Number {catalogue_number} already exists!', 'error')
                conn.close()
                return redirect(url_for('add_chemical'))  # Redirect back to the add page
            else:
                # Add the chemical to the database
                cursor.execute('''INSERT INTO Chemicals (CatalogueNumber, CASNumber, Location, Structure, MolecularWeight, Quantity, Barcode)
                                  VALUES (?, ?, ?, ?, ?, ?, ?)''',
                                  (catalogue_number, cas_number, location, structure, molecular_weight, quantity, barcode))
                conn.commit()
                conn.close()
                flash('Chemical added successfully!', 'success')
                return redirect(url_for('index'))  # Redirect to the homepage after adding the chemical
            
        else:
            return render_template('add.html')
    else:
        return redirect(url_for('login'))

@app.route('/delete/<catalogue_number>', methods=['DELETE'])
def delete_chemical(catalogue_number):
    if 'username' in session:
        conn = sqlite3.connect('chemistry_inventory.db')
        cursor = conn.cursor()
        
        try:
            cursor.execute('''DELETE FROM Chemicals WHERE CatalogueNumber = ?''', (catalogue_number,))
            conn.commit()
            conn.close()
            return jsonify({'success': True})
        except sqlite3.Error as e:
            conn.rollback()
            conn.close()
            return jsonify({'success': False, 'message': str(e)})
    else:
        return jsonify({'success': False, 'message': 'User not logged in'})

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = sqlite3.connect('chemistry_inventory.db')
        cursor = conn.cursor()
        
        # Check if the username and password are valid
        cursor.execute('''SELECT * FROM Users WHERE username = ? AND password = ?''', (username, password))
        user = cursor.fetchone()
        conn.close()
        
        if user:
            session['username'] = username
            flash('Logged in successfully!', 'success')
            return redirect(url_for('index'))  # Redirect to the index page after successful login
        else:
            flash('Invalid username or password. Please try again.', 'error')
            return redirect(url_for('login'))   # Redirect back to the login page if authentication fails
    else:
        return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = sqlite3.connect('chemistry_inventory.db')
        cursor = conn.cursor()
        
        # Check if the username already exists
        cursor.execute('''SELECT * FROM Users WHERE username = ?''', (username,))
        existing_user = cursor.fetchone()
        if existing_user:
            flash('Username already exists. Please choose a different username.', 'error')
            conn.close()
            return redirect(url_for('register'))  # Redirect back to the registration page
        else:
            # Insert the new user into the database
            cursor.execute('''INSERT INTO Users (username, password) VALUES (?, ?)''', (username, password))
            conn.commit()
            conn.close()
            flash('Account created successfully! You can now login.', 'success')
            return redirect(url_for('login'))  # Redirect to the login page after successful registration
    else:
        return render_template('register.html')

@app.route('/logout')
def logout():
    # Clear the session
    session.pop('username', None)
    flash('You have been logged out.', 'success')
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
