"""Authentication forms."""

from __future__ import annotations

from flask_wtf import FlaskForm
from wtforms import BooleanField, PasswordField, StringField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, Length, ValidationError

from database.models import User


class LoginForm(FlaskForm):
    """Login form."""

    username = StringField("Tên đăng nhập", validators=[DataRequired(), Length(min=3, max=80)])
    password = PasswordField("Mật khẩu", validators=[DataRequired()])
    remember_me = BooleanField("Ghi nhớ đăng nhập")
    submit = SubmitField("Đăng nhập")


class RegistrationForm(FlaskForm):
    """Registration form."""

    username = StringField("Tên đăng nhập", validators=[DataRequired(), Length(min=3, max=80)])
    email = StringField("Email", validators=[DataRequired(), Email()])
    full_name = StringField("Họ tên", validators=[Length(max=100)])
    phone = StringField("Số điện thoại", validators=[Length(max=20)])
    password = PasswordField("Mật khẩu", validators=[DataRequired(), Length(min=6)])
    password2 = PasswordField("Xác nhận mật khẩu", validators=[DataRequired(), EqualTo("password")])
    submit = SubmitField("Đăng ký")

    def validate_username(self, username: StringField) -> None:
        """Validate username uniqueness."""
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError("Tên đăng nhập đã tồn tại.")

    def validate_email(self, email: StringField) -> None:
        """Validate email uniqueness."""
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError("Email đã được sử dụng.")

