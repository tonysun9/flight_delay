import streamlit as st
from claude import generate_response

st.set_page_config(
    page_title="Flight Checker",
    page_icon=":airplane:",
    layout="centered",
    initial_sidebar_state="auto",
    menu_items=None,
)

# """
# <style>
# #MainMenu {visibility: hidden;}
# footer {visibility: hidden;}
# </style>
# """
hide_streamlit_style = """
            <style>
            footer {visibility: hidden;}
            </style>
            """
st.markdown(hide_streamlit_style, unsafe_allow_html=True)


st.title("Is my flight delayed?")

flight_number = st.text_input("Flight Number")
connecting_flight_number = st.text_input("Connecting Flight Number (Optional)")


if st.button("Run"):
    status_message = st.empty()  # placeholder for status message
    # st.write(
    #     "Collecting data for flight number {} and connecting flight number {}...".format(
    #         flight_number, connecting_flight_number
    #     )
    # )
    response = generate_response(flight_number, connecting_flight_number)

    # status_message.empty()
    st.write(response)

# Footer
st.markdown(
    """
    ---
    The information provided is based on trends and probabilities and should not replace official information from the airline.
    """,
    unsafe_allow_html=True,
)
