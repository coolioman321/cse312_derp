import React from 'react'
import '../App.css'

function Homepage() {
    const showAlert = () => {
        alert('Button clicked!')
    }

    return (
        <div className='headerText'>
            <h1>HELLO WORLD FROM FLASK</h1>
            <button onClick={showAlert}>Click Me</button>
        </div>
    )
}

export default Homepage