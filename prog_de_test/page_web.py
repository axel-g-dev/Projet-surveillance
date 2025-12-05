import streamlit as st
from code import init_streamlit_camera, process_frame

st.title("Surveillance vidéo")

start = st.button("Démarrer")
stop = st.button("Arrêter")

frame_placeholder = st.empty()

if start:
    st.session_state.run = True
    cap, f1, f2 = init_streamlit_camera()
    st.session_state.cap = cap
    st.session_state.f1 = f1
    st.session_state.f2 = f2

if stop:
    st.session_state.run = False

if st.session_state.get("run", False):
    display, next_f2, contours = process_frame(
        st.session_state.cap,
        st.session_state.f1,
        st.session_state.f2
    )

    if display is not None:
        frame_placeholder.image(display, channels="BGR")
        st.session_state.f1 = st.session_state.f2
        st.session_state.f2 = next_f2
