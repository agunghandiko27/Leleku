from . import db
from datetime import datetime
from flask_login import UserMixin

followers = db.Table('followers',
    db.Column('follower_id', db.Integer, db.ForeignKey('user.id')),
    db.Column('followed_id', db.Integer, db.ForeignKey('user.id'))
)

post_likes = db.Table('post_likes',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id')),
    db.Column('post_id', db.Integer, db.ForeignKey('post.id'))
)

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, server_default="Pengguna")
    username = db.Column(db.String(64), unique=True)
    email = db.Column(db.String(120), unique=True)
    password = db.Column(db.String(128))
    role = db.Column(db.String(20), default="user")
    bio = db.Column(db.String(255), default="")
    gender = db.Column(db.String(10), default="unspecified")
    birthdate = db.Column(db.String(20), default="")
    photo = db.Column(db.String(255), default="default.jpg")

    is_verified = db.Column(db.Boolean, default=False)
    otp_code = db.Column(db.String(6))
    otp_expiry = db.Column(db.DateTime)

    posts = db.relationship("Post", backref="user", lazy=True)

    sent_messages = db.relationship(
        "ChatMessage",
        foreign_keys="ChatMessage.sender_id",
        backref="sender",
        lazy=True
    )

    received_messages = db.relationship(
        "ChatMessage",
        foreign_keys="ChatMessage.receiver_id",
        backref="receiver",
        lazy=True
    )

    followed = db.relationship(
        'User',
        secondary=followers,
        primaryjoin=(followers.c.follower_id == id),
        secondaryjoin=(followers.c.followed_id == id),
        backref=db.backref('followers', lazy='dynamic'),
        lazy='dynamic'
    )

    def follow(self, user):
        if not self.is_following(user):
            self.followed.append(user)

    def unfollow(self, user):
        if self.is_following(user):
            self.followed.remove(user)

    def is_following(self, user):
        return self.followed.filter(followers.c.followed_id == user.id).count() > 0

    def has_liked_post(self, post):
        return post.liked_by.filter_by(id=self.id).count() > 0

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    text = db.Column(db.Text)
    image = db.Column(db.String(255))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    comments = db.relationship("Comment", backref="post", lazy=True, cascade="all, delete-orphan")
    liked_by = db.relationship(
        'User',
        secondary=post_likes,
        backref=db.backref('liked_posts', lazy='dynamic'),
        lazy='dynamic'
    )

    def like(self, user):
        if not self.is_liked_by(user):
            self.liked_by.append(user)

    def unlike(self, user):
        if self.is_liked_by(user):
            self.liked_by.remove(user)

    def is_liked_by(self, user):
        return self.liked_by.filter(post_likes.c.user_id == user.id).count() > 0

    def like_count(self):
        return self.liked_by.count()


class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey("post.id"))
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    text = db.Column(db.Text)
    image = db.Column(db.String(255))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User", backref="comments")

class ChatMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey("user.id", name="fk_sender_id"))
    receiver_id = db.Column(db.Integer, db.ForeignKey("user.id", name="fk_receiver_id"))
    text = db.Column(db.Text)
    image = db.Column(db.String(255), nullable=True)
    seen = db.Column(db.Boolean, default=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)


class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    recipient_id = db.Column(
        db.Integer,
        db.ForeignKey('user.id', name='fk_notification_recipient_id'),
        nullable=False
    )

    sender_id = db.Column(
        db.Integer,
        db.ForeignKey('user.id', name='fk_notification_sender_id'),
        nullable=False
    )

    message = db.Column(db.String(255), nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    recipient = db.relationship('User', foreign_keys=[recipient_id], backref='notifications_received')
    sender = db.relationship('User', foreign_keys=[sender_id])

class Story(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    image = db.Column(db.String(255), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref=db.backref('stories', lazy='dynamic', cascade="all, delete-orphan"))

    def is_expired(self):
        from datetime import timedelta
        return datetime.utcnow() > self.timestamp + timedelta(hours=24)


class StoryView(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    story_id = db.Column(db.Integer, db.ForeignKey('story.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    story = db.relationship('Story', backref=db.backref('views', lazy='dynamic', cascade="all, delete-orphan"))
    user = db.relationship('User')


class StoryLike(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    story_id = db.Column(db.Integer, db.ForeignKey('story.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    story = db.relationship('Story', backref=db.backref('likes', lazy='dynamic', cascade="all, delete-orphan"))
    user = db.relationship('User')
