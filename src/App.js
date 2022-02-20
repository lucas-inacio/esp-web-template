import React from 'react';
import { Button } from 'reactstrap';

import 'bootstrap/dist/css/bootstrap.min.css';
import './App.css';

function onClick() {
    fetch('/toggle', { method: 'POST' })
        .then((response) => {
            if (response.ok)
                console.log('OK')
            else
                console.log('NOT OK');
        });
}

const App = () => {
    return (
        <div className="h-100 d-flex justify-content-center align-items-center">
            <Button onClick={onClick}>Comuta LED</Button>
        </div>
    );
}

export default App;