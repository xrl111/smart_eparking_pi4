"""Authentication routes."""

from __future__ import annotations

from datetime import UTC, datetime
from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from auth.forms import LoginForm, RegistrationForm
from database.db import db
from database.models import User

from . import auth_bp


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """Login page."""
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.check_password(form.password.data) and user.is_active:
            login_user(user, remember=form.remember_me.data)
            user.last_login = datetime.now(UTC)
            db.session.commit()

            next_page = request.args.get("next")
            if not next_page or not next_page.startswith("/"):
                next_page = url_for("main.dashboard")
            return redirect(next_page)
        flash("Tên đăng nhập hoặc mật khẩu không đúng.", "error")
    return render_template("auth/login.html", form=form)


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    """Registration page."""
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(
            username=form.username.data,
            email=form.email.data,
            full_name=form.full_name.data,
            phone=form.phone.data,
            role="client",  # Default role
            is_active=True,
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash("Đăng ký thành công! Vui lòng đăng nhập.", "success")
        return redirect(url_for("auth.login"))
    return render_template("auth/register.html", form=form)


@auth_bp.route("/logout")
@login_required
def logout():
    """Logout."""
    logout_user()
    flash("Đã đăng xuất thành công.", "info")
    return redirect(url_for("auth.login"))

