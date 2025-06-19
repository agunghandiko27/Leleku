from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import db
from app.models import User, Post, Comment

admin = Blueprint('admin', __name__)

# Middleware: hanya admin yang boleh akses blueprint ini
@admin.before_request
@login_required
def admin_only():
    if current_user.role != 'admin':
        flash("Kamu tidak memiliki akses ke halaman admin.", "danger")
        return redirect(url_for('main.home'))

# Dashboard Admin
@admin.route('/admin', methods=['GET'])
def admin_dashboard():
    search_query = request.args.get('search')
    if search_query:
        users = User.query.filter(
            (User.username.ilike(f'%{search_query}%')) |
            (User.email.ilike(f'%{search_query}%'))
        ).order_by(User.id.desc()).all()
    else:
        users = User.query.order_by(User.id.desc()).all()
    return render_template('admin_panel.html', users=users)

# Toggle verifikasi centang biru
@admin.route('/admin/verify/<int:user_id>')
def verify_user(user_id):
    user = User.query.get_or_404(user_id)
    user.is_verified = not user.is_verified
    db.session.commit()
    flash("Status centang biru berhasil diperbarui.", "success")
    return redirect(url_for('admin.admin_dashboard'))

# Nonaktifkan user
@admin.route('/admin/disable/<int:user_id>')
def disable_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.role != 'disabled':
        user.role = 'disabled'
    else:
        user.role = 'user'
    db.session.commit()
    flash("Status akun user diperbarui.", "warning")
    return redirect(url_for('admin.admin_dashboard'))

# Hapus user
@admin.route('/admin/delete/<int:user_id>')
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash("Tidak dapat menghapus akun Anda sendiri.", "danger")
        return redirect(url_for('admin.admin_dashboard'))

    db.session.delete(user)
    db.session.commit()
    flash("User berhasil dihapus.", "danger")
    return redirect(url_for('admin.admin_dashboard'))

#V2

@admin.route('/admin/statistics')
def admin_statistics():
    total_users = User.query.count()
    total_posts = Post.query.count()
    total_comments = Comment.query.count()

    return render_template('admin_statistics.html',
                           total_users=total_users,
                           total_posts=total_posts,
                           total_comments=total_comments)

@admin.route('/admin/posts')
def manage_posts():
    posts = Post.query.order_by(Post.id.desc()).all()
    return render_template('admin_posts.html', posts=posts)

@admin.route('/admin/posts/delete/<int:post_id>')
def delete_post(post_id):
    post = Post.query.get_or_404(post_id)
    db.session.delete(post)
    db.session.commit()
    flash("Postingan berhasil dihapus.", "danger")
    return redirect(url_for('admin.manage_posts'))

@admin.route('/admin/comments')
def manage_comments():
    comments = Comment.query.order_by(Comment.id.desc()).all()
    return render_template('admin_comments.html', comments=comments)

@admin.route('/admin/comments/delete/<int:comment_id>')
def delete_comment(comment_id):
    comment = Comment.query.get_or_404(comment_id)
    db.session.delete(comment)
    db.session.commit()
    flash("Komentar berhasil dihapus.", "danger")
    return redirect(url_for('admin.manage_comments'))
