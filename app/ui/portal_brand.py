"""Club identity for the portal; all personal text is escaped before rendering."""
import base64
from html import escape
from pathlib import Path

import streamlit as st
from ui.theme import inject_ohiggins_theme


def crest():
    data = (Path(__file__).resolve().parents[1] / 'assets/OHigginsFC.png').read_bytes()
    return 'data:image/png;base64,' + base64.b64encode(data).decode('ascii')


def inject_portal_brand():
    inject_ohiggins_theme()
    st.markdown('''<style>
    .stApp {background:#f3f7fb;color:#132e45;}
    [data-testid="stMainBlockContainer"] {max-width:1440px;padding:2rem 3rem 4rem;}
    [data-testid="stHeader"] {background:transparent;}
    .club-masthead {display:flex;align-items:center;justify-content:space-between;gap:24px;
        padding:24px 30px;background:#102e46;border-radius:18px;border-bottom:5px solid #75b9e5;
        margin-bottom:16px;color:white;box-shadow:0 12px 28px #173e5712;}
    .club-brand {display:flex;gap:20px;align-items:center;}
    .club-masthead img {width:62px;height:76px;object-fit:contain;}
    .club-name {font-size:25px;font-weight:800;letter-spacing:.03em;color:white;}
    .club-overline {font-size:11px;letter-spacing:.16em;font-weight:750;color:#b4d9f2;line-height:1.8;}
    .club-account {text-align:right;color:white;font-size:14px;}
    .club-role {display:inline-block;background:#ffffff14;border:1px solid #ffffff35;
        border-radius:100px;padding:5px 12px;margin-top:6px;font-size:11px;color:#d9ecfa;}
    .stApp .club-masthead .club-role {color:#e5f2fc!important;background:#244b66!important;}
    .club-welcome {padding:26px 0 20px;}
    .club-welcome h1 {font-size:clamp(26px,3vw,38px);letter-spacing:-.035em;color:#132e45;margin:8px 0;}
    .club-welcome p {color:#556e82;font-size:16px;max-width:650px;}
    .club-kicker {color:#276990;font-size:11px;letter-spacing:.16em;font-weight:800;}
    .club-card {background:white;border:1px solid #dce7ee;border-top:4px solid #75b9e5;
        border-radius:16px;padding:28px;min-height:150px;margin-bottom:10px;}
    .club-card-head {display:flex;justify-content:space-between;align-items:center;margin-bottom:20px;}
    .club-card-number {font-size:27px;font-weight:800;color:#c3dbe9;}
    .club-card h2 {color:#102e46;font-size:28px;margin:0 0 4px;}
    .club-card h3 {color:#39779f;font-size:16px;margin:0 0 14px;}
    .club-card p {color:#52697b;line-height:1.65;font-size:14px;}
    .club-login {position:relative;overflow:hidden;background:linear-gradient(115deg,#102e46,#1c4b6b);
        border-radius:22px;padding:28px 36px;margin:12px 0 24px;border-bottom:6px solid #75b9e5;}
    .club-login:after {content:'';position:absolute;right:-55px;top:-95px;width:340px;height:340px;
        border:1px solid #ffffff18;border-radius:50%;box-shadow:0 0 0 65px #ffffff04,0 0 0 130px #ffffff04;pointer-events:none;}
    .club-login img {width:80px;height:100px;object-fit:contain;margin-bottom:20px;}
    .club-login h1 {color:white!important;font-size:clamp(30px,4vw,48px);line-height:1.12;max-width:700px;margin:10px 0 16px;}
    .club-login p {color:#c8dfef;max-width:580px;font-size:16px;}
    [data-testid="stForm"] {background:white;border:1px solid #dce7ee;border-radius:16px;padding:26px;}
    .st-key-portal_module [role="radiogroup"] {gap:8px;flex-wrap:wrap;}
    .st-key-portal_module [data-testid="stRadio"] label {background:white;border:1px solid #d7e4ed;border-radius:10px;padding:9px 16px;}
    .st-key-portal_module label:has(input:checked) {background:#e0f0fc;border-color:#4f8fcc;}
    button[kind="primary"] {background:#286c99!important;border-color:#286c99!important;color:white!important;}
    button[kind="primary"]:hover {background:#1b537b!important;border-color:#1b537b!important;}
    button:focus-visible, input:focus-visible {outline:3px solid #75b9e5!important;outline-offset:2px;}
    .stApp [class*="st-key-nav_"] button[kind="primary"] {background:#286c99!important;border-color:#286c99!important;}
    .stApp [class*="st-key-nav_"] button[kind="primary"] p {color:#fff!important;}
    button[kind="primary"] p {color:white!important;}
    [data-testid="stCaptionContainer"] p {color:#496477!important;}
    [data-testid="stWidgetLabel"] p {color:#294b65!important;}
    input::placeholder {color:#496477!important;opacity:1!important;}
    [data-testid="stAppViewContainer"] {background:#f3f7fb!important;}
    .st-key-portal_module label:has(input:checked) p {color:#173f5b!important;font-weight:750;}
    .st-key-portal_module label:focus-within {outline:3px solid #286c99;outline-offset:3px;}

    .st-key-portal_login_shell {max-width:440px!important;margin:1rem auto 3rem!important;}
    .st-key-portal_login_shell .club-login {text-align:center;background:transparent;border:0;
        border-radius:0;padding:0 16px 8px;margin:0;}
    .st-key-portal_login_shell .club-login:after {display:none;}
    .st-key-portal_login_shell .club-login img {width:96px;height:120px;margin:0 auto 16px;display:block;}
    .st-key-portal_login_shell .club-overline {color:#286c99;font-size:12px;letter-spacing:.2em;}
    .st-key-portal_login_shell .club-login h1 {color:#132e45!important;font-size:28px;margin:10px 0 16px;}
    .st-key-portal_login_shell [data-testid="stForm"] {padding:30px!important;background:white!important;
        border:1px solid #d5e3ee!important;border-radius:20px!important;box-shadow:0 15px 45px #143c5710;}
    .st-key-portal_login_shell [data-baseweb="input"] {background:#f4f8fc!important;
        border:1px solid #b4cada!important;border-radius:9px!important;min-height:48px;}
    .st-key-portal_login_shell [data-baseweb="input"]:focus-within {border-color:#286c99!important;box-shadow:0 0 0 3px #75b9e530;}
    .st-key-portal_login_shell input {background:transparent!important;color:#132e45!important;}
    .st-key-portal_login_shell label p {font-weight:650!important;color:#294b65!important;}
    .st-key-portal_login_shell button[kind="primary"] {min-height:48px;margin-top:10px;}
    .st-key-portal_login_shell [data-testid="stElementContainer"],
    .st-key-portal_login_shell [data-testid="stMarkdown"],
    .st-key-portal_login_shell .club-login {width:100%!important;max-width:100%!important;}
    .st-key-portal_login_shell .club-login h1 {max-width:100%!important;}
    .stApp .st-key-portal_login_shell [data-testid="stFormSubmitButton"] button,
    .stApp .st-key-portal_login_shell [data-testid="stFormSubmitButton"] button p {
        background:#286c99!important;color:#ffffff!important;}
    .st-key-portal_login_shell [data-testid="stFormSubmitButton"] button {min-height:48px!important;}
    .stApp .st-key-portal_login_shell [data-baseweb="input"] {border:1px solid #59788f!important;background:#f4f8fc!important;}
    .stApp .st-key-portal_login_shell input {background:#f4f8fc!important;color:#132e45!important;}
    @media(max-width:700px) {
        [data-testid="stMainBlockContainer"] {padding:1rem 1rem 3rem;}
        .club-masthead {padding:20px;align-items:flex-start;flex-direction:column;gap:12px;}
        .club-account {text-align:left;}.club-name{font-size:22px;}
        .club-login {padding:28px 24px;}.club-card {min-height:0;padding:24px;}
    }
    </style>''', unsafe_allow_html=True)


def masthead(user):
    role = 'Administración' if user['role'] == 'admin' else 'Scouting'
    st.markdown(f'''<div class="club-masthead"><div class="club-brand">
    <img src="{crest()}" alt="Escudo de O’Higgins FC"><div>
    <div class="club-name">O’HIGGINS FC</div>
    <div class="club-overline">PLATAFORMA DEPORTIVA</div></div></div>
    <div class="club-account">{escape(user['display_name'])}<br><span class="club-role">{role}</span></div></div>''', unsafe_allow_html=True)


def login_identity():
    st.markdown(f'''<div class="club-login"><img src="{crest()}" alt="Escudo de O’Higgins FC">
    <div class="club-overline">O’HIGGINS FC</div>
    <h1>Portal deportivo</h1>
    </div>''', unsafe_allow_html=True)


def welcome(user):
    st.markdown('<div class="club-welcome"><h1>Áreas de trabajo</h1></div>', unsafe_allow_html=True)


def module_card(number, title, subtitle):
    st.markdown(f'''<div class="club-card"><div class="club-card-head"><h2>{escape(title)}</h2>
    <span class="club-card-number">{escape(number)}</span></div>
    <h3>{escape(subtitle)}</h3></div>''', unsafe_allow_html=True)
