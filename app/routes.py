from flask import Blueprint, render_template, request, redirect, url_for, session, flash, current_app
from .models import Notification
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
from flask_mail import Message
from app import mail
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy import or_, and_
from .models import db, User, Post, Comment, Story, StoryLike, StoryView
from flask import jsonify, send_from_directory
from flask_login import login_required, current_user, login_user, logout_user
from datetime import datetime, timedelta
from .models import ChatMessage
from sqlalchemy.orm import joinedload
import random
import uuid
import re
import os

def send_otp_email_custom(email, otp):
    subject = "Kode OTP Verifikasi Akun"
    body = f"Kode OTP kamu adalah: {otp}\nKode ini berlaku selama 5 menit."

    msg = Message(subject, recipients=[email], body=body)
    mail.send(msg)

main = Blueprint("main", __name__)
s = URLSafeTimedSerializer("agungh123")

# ------------------- Halaman Splash -------------------
@main.route("/")
def splash():
    return render_template("splash.html")

# ------------------- Login -------------------
@main.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if request.is_json:
            data = request.get_json()
            identifier = data.get("identity")
            password = data.get("password")
            remember = data.get("remember", False)
        else:
            identifier = request.form["identity"]
            password = request.form["password"]
            remember = "remember" in request.form

        user = (
            User.query.filter_by(email=identifier).first()
            if "@" in identifier
            else User.query.filter_by(username=identifier).first()
        )

        if not user or not check_password_hash(user.password, password):
            if request.is_json:
                return jsonify(success=False, message="Email/nama pengguna atau password salah")
            return render_template("login.html", error="Email/nama pengguna atau password salah")

        if not user.is_verified and user.role != 'admin':
            if request.is_json:
                return jsonify(success=False, message="Akun belum diverifikasi. Masukkan kode OTP.")
            flash("Akun belum diverifikasi. Masukkan kode OTP.", "warning")
            return redirect(url_for("main.verify_otp", user_id=user.id))

        login_user(user, remember=remember)
        session["user_id"] = user.id
        session["username"] = user.username

        if request.is_json:
            return jsonify(success=True, redirect="/home")

        next_page = request.args.get("next")
        return redirect(next_page) if next_page else redirect("/home")

    return render_template("login.html")

# ------------------- Register -------------------
@main.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        username = request.form["username"].strip()
        email = request.form["email"].strip()
        password = request.form["password"]
        confirm = request.form["confirm"]

        if not name or not re.match(r"^[a-zA-ZÀ-ÿ\s.,]+$", name):
            return jsonify({"error": "Nama lengkap tidak valid. Hanya huruf dan tanda baca umum diperbolehkan."}), 400

        if password != confirm:
            return jsonify({"error": "Password dan konfirmasi tidak cocok"}), 400

        if len(password) < 8 or not any(c.isalpha() for c in password) or not any(c.isdigit() for c in password):
            return jsonify({"error": "Password harus minimal 8 karakter, mengandung huruf dan angka"}), 400

        if User.query.filter_by(username=username, is_verified=True).first():
            return jsonify({"error": "Username sudah digunakan"}), 400

        if User.query.filter_by(email=email, is_verified=True).first():
            return jsonify({"error": "Email sudah terdaftar"}), 400

        hashed_pw = generate_password_hash(password)

        otp = str(random.randint(100000, 999999))
        expiry = datetime.utcnow() + timedelta(minutes=5)

        session["pending_user"] = {
            "name": name,
            "username": username,
            "email": email,
            "password": hashed_pw,
            "otp_code": otp,
            "otp_expiry": expiry.isoformat()
        }

        send_otp_email_custom(email, otp)

        return jsonify({
            "message": "Kode OTP telah dikirim ke email kamu. Silakan cek email untuk verifikasi akun.",
            "redirect_url": url_for("main.verify_otp_temp")
        })

    return render_template("register.html")


@main.route('/check_user', methods=['POST'])
def check_user():
    data = request.get_json()
    username = data.get('username')
    email = data.get('email')

    response = {}

    if username and User.query.filter_by(username=username).first():
        response['username_error'] = 'Username sudah digunakan'

    if email and User.query.filter_by(email=email).first():
        response['email_error'] = 'Email sudah terdaftar'

    return jsonify(response)

@main.route("/verify_otp_temp", methods=["GET", "POST"])
def verify_otp_temp():
    pending = session.get("pending_user")
    if not pending:
        flash("Session verifikasi tidak ditemukan. Silakan daftar ulang.", "danger")
        return redirect(url_for("main.register"))

    expiry = datetime.fromisoformat(pending["otp_expiry"])

    if request.method == "POST":
        otp_input = request.form.get("otp", "").strip()

        if otp_input == pending["otp_code"] and datetime.utcnow() < expiry:
            user = User(
                name=pending["name"],
                username=pending["username"],
                email=pending["email"],
                password=pending["password"],
                is_verified=True
            )
            db.session.add(user)
            db.session.commit()

            session.pop("pending_user", None)
            flash("Verifikasi berhasil! Silakan login.", "success")
            return redirect(url_for("main.login"))
        else:
            flash("Kode OTP salah atau sudah kadaluarsa.", "danger")

    return render_template("verify_otp.html", user=pending, otp_expiry=expiry)

@main.route("/resend_otp")
def resend_otp():
    pending = session.get("pending_user")
    if not pending:
        flash("Session tidak ditemukan. Silakan daftar ulang.", "danger")
        return redirect(url_for("main.register"))

    expiry = datetime.fromisoformat(pending["otp_expiry"])
    if datetime.utcnow() < expiry:
        remaining = int((expiry - datetime.utcnow()).total_seconds())
        flash(f"Tunggu {remaining} detik sebelum mengirim ulang OTP.", "warning")
        return redirect(url_for("main.verify_otp_temp"))

    # Generate OTP baru
    otp = str(random.randint(100000, 999999))
    expiry_new = datetime.utcnow() + timedelta(minutes=5)

    # Update session
    pending["otp_code"] = otp
    pending["otp_expiry"] = expiry_new.isoformat()
    session["pending_user"] = pending

    # Kirim ulang email OTP
    send_otp_email_custom(pending["email"], otp)

    flash("Kode OTP baru telah dikirim ke email kamu.", "info")
    return redirect(url_for("main.verify_otp_temp"))

# ------------------- Home -------------------
@main.route('/home', methods=['GET'])
@login_required
def home():
    posts = Post.query.order_by(Post.timestamp.desc()).all()

    users_with_story = []
    users = User.query.all()
    for user in users:
        stories = Story.query.filter_by(user_id=user.id).order_by(Story.timestamp.desc()).all()
        if stories:
            user.latest_story = stories[0]  # latest story per user
            users_with_story.append(user)

    return render_template('home.html', posts=posts, users_with_story=users_with_story)

# ------------------- Upload Story -------------------
@main.route('/story/upload', methods=['GET', 'POST'])
@login_required
def story_preview():
    if request.method == 'POST':
        file = request.files['story_file']
        if file and file.filename != '':

            if not file.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
                flash("File bukan gambar valid!")
                return redirect(url_for('main.story_preview'))

            ext = os.path.splitext(file.filename)[1]
            unique_filename = f"{uuid.uuid4().hex}{ext}"

            upload_path = os.path.join(current_app.root_path, 'static/story_uploads', unique_filename)
            file.save(upload_path)

            story = Story(user_id=current_user.id, image=unique_filename)
            db.session.add(story)
            db.session.commit()
            return redirect(url_for('main.home'))

    return render_template('story_preview.html', user=current_user)

# ------------------- Story View -------------------
@main.route('/story/view/<int:user_id>/<int:index>')
@login_required
def view_story(user_id, index):
    user = User.query.get_or_404(user_id)
    stories = Story.query.filter_by(user_id=user.id).order_by(Story.timestamp.asc()).all()

    if index >= len(stories):
        return redirect(url_for('main.home'))

    current_story = stories[index]
    liked = StoryLike.query.filter_by(story_id=current_story.id, user_id=current_user.id).first() is not None

    return render_template(
        'story_view.html',
        user=user,
        stories=stories,
        index=index,
        story=current_story,
        liked=liked
    )

# ------------------- Like Story -------------------
@main.route('/story/like/<int:story_id>', methods=['POST'])
@login_required
def like_story(story_id):
    like = StoryLike.query.filter_by(story_id=story_id, user_id=current_user.id).first()
    if like:
        db.session.delete(like)
    else:
        like = StoryLike(story_id=story_id, user_id=current_user.id)
        db.session.add(like)
    db.session.commit()
    return '', 204

# ------------------- Delete Story -------------------
@main.route('/story/delete/<int:story_id>')
@login_required
def delete_story(story_id):
    story = Story.query.get_or_404(story_id)
    if story.user_id == current_user.id:

        # Hapus semua like & view story
        StoryLike.query.filter_by(story_id=story.id).delete()
        StoryView.query.filter_by(story_id=story.id).delete()

        # Hapus file dari folder jika ada
        if story.image:
            file_path = os.path.join(current_app.root_path, 'static/story_uploads', story.image)
            if os.path.isfile(file_path):
                try:
                    os.remove(file_path)
                except Exception as e:
                    print(f"Gagal menghapus file: {e}")

        db.session.delete(story)
        db.session.commit()

    return redirect(url_for('main.home'))

# ------------------- Reply Story (Chat Message) -------------------
@main.route('/story/reply/<int:story_id>', methods=['POST'])
@login_required
def reply_story(story_id):
    message = request.form['message']
    story = Story.query.get_or_404(story_id)
    receiver_id = story.user_id
    new_message = ChatMessage(sender_id=current_user.id, receiver_id=receiver_id, text=message)
    db.session.add(new_message)
    db.session.commit()
    return redirect(url_for('main.view_story', user_id=story.user_id, index=0))

@main.route("/create_post", methods=["GET", "POST"])
@login_required
def create_post():
    if request.method == "POST":
        text = request.form.get("text", "")
        image_file = request.files.get("image")

        filename = None
        if image_file and image_file.filename:
            filename = secure_filename(image_file.filename)
            image_path = os.path.join(current_app.root_path, "static/uploads", filename)
            image_file.save(image_path)

        new_post = Post(user_id=current_user.id, text=text, image=filename)
        db.session.add(new_post)
        db.session.commit()
        flash("Postingan berhasil dikirim!", "success")
        return redirect(url_for("main.home"))

    return render_template("create_post.html")

@main.route('/like/<int:post_id>', methods=['POST'])
@login_required
def like_post(post_id):
    post = Post.query.get_or_404(post_id)

    if post.is_liked_by(current_user):
        post.unlike(current_user)
        status = 'unliked'
    else:
        post.like(current_user)
        status = 'liked'

    db.session.commit()

    return jsonify({
        'status': status,
        'likes_count': post.like_count(),
        'comments_count': len(post.comments)
    })

@main.route('/comments/<int:post_id>')
@login_required
def view_comments(post_id):
    post = Post.query.get_or_404(post_id)
    return render_template('view_comments.html', post=post)

@main.route('/comment/<int:post_id>', methods=['POST'])
@login_required
def comment_post(post_id):
    if not request.is_json:
        return jsonify({"status": "error", "message": "Invalid request"}), 400

    data = request.get_json()
    text = data.get('text', '').strip()

    if not text:
        return jsonify({"status": "error", "message": "Comment cannot be empty"}), 400

    post = Post.query.get_or_404(post_id)
    
    comment = Comment(user_id=current_user.id, post_id=post.id, text=text)
    db.session.add(comment)
    db.session.commit()

    return jsonify({
        "status": "success",
        "comment": {
            "id": comment.id,
            "text": comment.text,
            "user": current_user.name,
            "user_id": current_user.id,
            "created_at": comment.created_at.strftime("%Y-%m-%d %H:%M") if hasattr(comment, 'created_at') else ""
        }
    }), 201

@main.route('/comment/edit/<int:comment_id>', methods=['POST'])
@login_required
def edit_comment(comment_id):
    comment = Comment.query.get_or_404(comment_id)

    if comment.user_id != current_user.id:
        return jsonify({'status': 'unauthorized'}), 403

    if not request.is_json:
        return jsonify({'status': 'error', 'message': 'Invalid request format'}), 400

    data = request.get_json()
    new_text = data.get("text", "").strip()

    if not new_text:
        return jsonify({'status': 'error', 'message': 'Text cannot be empty'}), 400

    comment.text = new_text
    db.session.commit()

    return jsonify({'status': 'success', 'new_text': comment.text})

@main.route('/comment/delete/<int:comment_id>', methods=['POST'])
@login_required
def delete_comment(comment_id):
    comment = Comment.query.get_or_404(comment_id)

    if comment.user_id != current_user.id:
        return jsonify({'status': 'unauthorized'}), 403

    post_id = comment.post_id
    db.session.delete(comment)
    db.session.commit()

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return jsonify({'status': 'success', 'comment_id': comment_id})

    return redirect(url_for('main.view_comments', post_id=post_id))

#-----------Pencarian---------#
@main.route("/search")
@login_required
def search():
    q = request.args.get("q", "").strip().lower()
    users = []
    posts = []

    if q:
        users = User.query.filter(
            User.username.ilike(f"%{q}%"),
            User.is_verified == True
        ).all()

        posts = Post.query.join(User).filter(
            Post.text.ilike(f"%{q}%"),
            User.is_verified == True
        ).all()

    return jsonify({
        "users": [{
            "id": u.id,
            "username": u.username,
            "photo": u.photo or "default.jpg"
        } for u in users],
        "posts": [{
            "id": p.id,
            "content": p.text,
            "username": p.user.username
        } for p in posts]
    })

#---------Notif-------
@main.route('/notifications')
@login_required
def notifications():
    notifs = Notification.query.filter_by(recipient_id=current_user.id).order_by(Notification.timestamp.desc()).all()
    return render_template('notifications.html', notifications=notifs)

#-----------follow/unfollow-----------
@main.route("/follow/<int:user_id>", methods=["POST"])
@login_required
def toggle_follow(user_id):
    target_user = User.query.get_or_404(user_id)

    if target_user.id == current_user.id:
        if request.is_json:
            return jsonify({"success": False, "message": "Tidak dapat mengikuti diri sendiri."}), 400
        flash("Tidak dapat mengikuti diri sendiri.", "danger")
        return redirect(url_for("main.profile", username=target_user.username))

    is_following = current_user.is_following(target_user)

    if is_following:
        current_user.unfollow(target_user)
        db.session.commit()
        msg = f"Kamu berhenti mengikuti {target_user.username}"
        status = False
    else:
        current_user.follow(target_user)
        db.session.commit()
        msg = f"Kamu mulai mengikuti {target_user.username}"
        status = True

    if request.is_json:
        return jsonify({
            "success": True,
            "following": status,
            "followers_count": target_user.followers.count(),
            "message": msg
        })

    flash(msg, "success" if status else "info")
    return redirect(url_for("main.profile", username=target_user.username))

# ------------------- Daftar Inbox Chat -------------------
@main.route("/messages_list")
@login_required
def messages_list():
    from sqlalchemy import or_

    # Ambil semua pesan yang melibatkan user login, urutkan terbaru dulu
    all_messages = ChatMessage.query.filter(
        or_(
            ChatMessage.sender_id == current_user.id,
           ChatMessage.receiver_id == current_user.id
        )
    ).order_by(ChatMessage.timestamp.desc()).all()

    seen_pairs = set()
    chats = []

    for msg in all_messages:
        # buat pasangan unik dari id
        pair = tuple(sorted([msg.sender_id, msg.receiver_id]))
        if pair not in seen_pairs:
            seen_pairs.add(pair)
            # tentukan siapa lawan bicara
            user = msg.receiver if msg.sender_id == current_user.id else msg.sender
            chats.append({
                "user": user,
                "message": msg
            })

    return render_template("messages_list.html", chats=chats)

@main.route("/messages/<int:user_id>")
@login_required
def messages(user_id):
    receiver = User.query.get_or_404(user_id)

    messages = ChatMessage.query.filter(
        ((ChatMessage.sender_id == current_user.id) & (ChatMessage.receiver_id == receiver.id)) |
        ((ChatMessage.sender_id == receiver.id) & (ChatMessage.receiver_id == current_user.id))
    ).order_by(ChatMessage.timestamp).all()

    for msg in messages:
        if msg.receiver_id == current_user.id:
            msg.seen = True
    db.session.commit()

    return render_template("messages.html", receiver=receiver, messages=messages)

@main.route("/send_message", methods=["POST"])
@login_required
def send_message():
    text = request.form.get("text", "")
    receiver_id = request.form.get("receiver_id")
    image = request.files.get("image")
    filename = None

    if image:
        filename = secure_filename(f"{datetime.now().timestamp()}_{image.filename}")
        image_path = os.path.join("static", "messages", filename)
        os.makedirs(os.path.dirname(image_path), exist_ok=True)
        image.save(image_path)

    msg = ChatMessage(
        sender_id=current_user.id,
        receiver_id=receiver_id,
        text=text,
        image=filename,
        timestamp=datetime.utcnow(),
        seen=False
    )
    db.session.add(msg)
    db.session.commit()

    # Socket.IO emit (kalau pakai)
    from app import socketio
    socketio.emit("new_message", {
        "sender_id": current_user.id,
        "receiver_id": int(receiver_id),
        "text": text,
        "image": filename,
        "time": msg.timestamp.strftime("%H:%M")
    })

    return jsonify({"success": True})

@main.route("/users_list")
@login_required
def users_list():
    users = User.query.filter(User.id != current_user.id).all()
    return render_template("users_list.html", users=users)

@main.route('/delete_chat/<int:receiver_id>', methods=['POST'])
@login_required
def delete_chat(receiver_id):
    try:
        messages = ChatMessage.query.filter(
            or_(
                and_(ChatMessage.sender_id == current_user.id, ChatMessage.receiver_id == receiver_id),
                and_(ChatMessage.sender_id == receiver_id, ChatMessage.receiver_id == current_user.id)
            )
        ).all()

        print("Jumlah pesan ditemukan:", len(messages))  # Debug print

        for msg in messages:
            if msg.image:
                path = os.path.join(current_app.root_path, 'static/messages', msg.image)
                if os.path.exists(path):
                    os.remove(path)
            db.session.delete(msg)

        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        print("Error:", e)
        return jsonify({'success': False, 'error': str(e)})

# ------------------- Edit Postingan -------------------
@main.route("/edit_post/<int:post_id>", methods=["GET", "POST"])
def edit_post(post_id):
    post = Post.query.get_or_404(post_id)
    if session.get("user_id") != post.user_id:
        flash("Akses ditolak!", "danger")
        return redirect("/home")

    if request.method == "POST":
        post.text = request.form["text"]
        image = request.files.get("image")

        if image and image.filename != "":
            filename = secure_filename(image.filename)
            image_path = os.path.join(current_app.root_path, "static/uploads", filename)
            image.save(image_path)
            post.image = filename

        db.session.commit()
        flash("Postingan diperbarui", "success")
        return redirect("/home")

    return render_template("edit_post.html", post=post)


# ------------------- Hapus Postingan -------------------
@main.route("/delete_post/<int:post_id>", methods=["POST"])
def delete_post(post_id):
    post = Post.query.get_or_404(post_id)
    if session.get("user_id") != post.user_id:
        flash("Akses ditolak!", "danger")
        return redirect("/home")

    db.session.delete(post)
    db.session.commit()
    flash("Postingan dihapus", "success")
    return redirect("/home")


# ------------------- Profil -------------------
@main.route("/profile/<username>")
def profile(username):
    try:
        user = User.query.filter_by(username=username).one()
    except NoResultFound:
        return "Pengguna tidak ditemukan", 404

    followers = user.followers.all()
    following = user.followed.all()

    return render_template("profile.html", user=user, current_user=current_user, followers=followers, following=following)

# ------------------- Redirect ke Profil Sendiri -------------------
@main.route("/profile/")
def my_profile():
    if "user_id" not in session:
        return redirect(url_for("main.login"))

    user = User.query.get(session["user_id"])
    return redirect(url_for("main.profile", username=user.username))

# ------------------- Edit Profil -------------------
@main.route("/edit_profile", methods=["GET", "POST"])
def edit_profile():
    if "user_id" not in session:
        return redirect(url_for("main.login"))

    user = User.query.get(session["user_id"])

    if request.method == "POST":
        new_name = request.form.get("name", user.name)
        new_username = request.form.get("username", user.username)
        new_bio = request.form.get("bio", "")
        new_gender = request.form.get("gender", "")

        # Validasi username unik (selain dirinya sendiri)
        existing_user = User.query.filter_by(username=new_username).first()
        if existing_user and existing_user.id != user.id:
            flash("Username sudah digunakan oleh pengguna lain.", "danger")
            return redirect(url_for("main.edit_profile"))

        # Simpan perubahan
        user.name = new_name
        user.username = new_username
        user.bio = new_bio
        user.gender = new_gender

        # Tambahan aman: pastikan direktori foto ada
        photo_file = request.files.get("photo")
        if photo_file and photo_file.filename:
            import os, uuid
            filename = f"file_{uuid.uuid4().hex}.png"
            photo_path = os.path.join("app", "static", "images", filename)
            os.makedirs(os.path.dirname(photo_path), exist_ok=True)  # ✅ pastikan folder ada
            photo_file.save(photo_path)
            user.photo = filename

        db.session.commit()
        flash("Profil berhasil diperbarui.", "success")
        return redirect(url_for("main.profile", username=user.username))

    return render_template("edit_profile.html", user=user)

# ------------------- Lupa Password -------------------
@main.route("/forgot", methods=["GET", "POST"])
def forgot():
    if request.method == "POST":
        email = request.form["email"]
        user = User.query.filter_by(email=email).first()

        if user:
            token = s.dumps(email, salt='reset-password')
            reset_link = url_for('main.reset_token', token=token, _external=True)

            msg = Message("Reset Password LELE", sender="agunghandiko2000@gmail.com", recipients=[email])
            msg.body = f"Klik link berikut untuk reset password Anda:\n{reset_link}\n\nLink berlaku selama 2 menit."

            try:
                from app import mail
                mail.send(msg)
                return render_template("forgot.html", message="Link reset telah dikirim ke email.")
            except Exception:
                return render_template("forgot.html", error="Gagal mengirim email. Coba lagi.")
        else:
            return render_template("forgot.html", error="Email tidak ditemukan.")

    return render_template("forgot.html")


# ------------------- Reset Password -------------------
@main.route("/reset/<token>", methods=["GET", "POST"])
def reset_token(token):
    try:
        email = s.loads(token, salt='reset-password', max_age=120)
    except SignatureExpired:
        return render_template("reset.html", error="Link telah kedaluwarsa.")
    except BadSignature:
        return render_template("reset.html", error="Token tidak valid.")

    user = User.query.filter_by(email=email).first()
    if not user:
        return render_template("reset.html", error="Pengguna tidak ditemukan.")

    if request.method == "POST":
        password = request.form["password"]
        confirm = request.form["confirm"]

        if password != confirm:
            return render_template("reset.html", error="Password dan konfirmasi tidak cocok.")

        if len(password) < 8 or not any(c.isalpha() for c in password) or not any(c.isdigit() for c in password):
            return render_template("reset.html", error="Password harus minimal 8 karakter, mengandung huruf dan angka.")

        user.password = generate_password_hash(password)
        db.session.commit()
        return redirect(url_for("main.login"))

    return render_template("reset.html")


# ------------------- Logout -------------------
@main.route("/logout")
def logout():
    logout_user()
    session.clear()
    return redirect(url_for("main.login"))
