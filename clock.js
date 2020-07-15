
var mqtt;

function mqtt_connect() {
    host = '192.168.99.999'
    port = 1884;
    console.log('connecting to '+ host +' '+ port)
    t = new Date().getTime()
    mqtt = new Paho.MQTT.Client(host,port,'client'+t)
    options = {
	timeout: 3,
	userName: 'xxxxxx',
	password: 'yyyyyy',
	onSuccess: mqtt_onconnect,
	onFailure: mqtt_onFailure,
    }
    mqtt.onMessageArrived = mqtt_onMessageArrived
    mqtt.connect(options);
}
function mqtt_onFailure(message) {
    console.log('mqtt connect failed');
    setTimeout(mqtt_connect, 2000);
}


// Note, make sure mqtt publish retain bit is set, so these values get set correctly on reload

function mqtt_onMessageArrived(msg){
    out_msg = 'mqtt message received: ' + msg.destinationName + ' => ' + msg.payloadString;
    console.log(out_msg);
    if (msg.destinationName == 'sensor/Outside Temperature') {
	console.log('out temp update')
	document.getElementById('tout').innerHTML = msg.payloadString
    }
    else if (msg.destinationName == 'sensor/Bedroom Temperature') {
	document.getElementById('tbed').innerHTML = msg.payloadString
    }
    else if (msg.destinationName == 'sensor/Upstairs Temperature') {
	document.getElementById('tup').innerHTML = msg.payloadString
    }
    else if (msg.destinationName == 'ha/speech') {
	document.getElementById('speech').innerHTML = msg.payloadString
    }
    else if (msg.destinationName == 'mh/hvac/summary') {
	document.getElementById('hvac').innerHTML = msg.payloadString
    }
    else if (msg.destinationName == 'ha/sunevent') {
//	if (msg.payloadString == 'sunriseEnd' || msg.payloadString == 'goldenHourEnd') {
	if (msg.payloadString == 'day') {
	    my_color = '#ffffff';
	}
	if (msg.payloadString == 'night') {
	    my_color = "#666666";
	}
	if (my_color) {
	    console.log('set color to ' + my_color);
	    let my_divs = document.querySelectorAll('div');
	    console.log('divs=' + my_divs);
	    for (let my_div of my_divs) {
		console.log('div=' + my_div);
		my_div.style.color = my_color;
	    }
	}
    }

}

function mqtt_onconnect() {
    console.log('mqtt connected')
    mqtt.subscribe('sensor/+')
    mqtt.subscribe('ha/speech')
    mqtt.subscribe('ha/sunevent')
    mqtt.subscribe('mh/hvac/summary')
    message = new Paho.MQTT.Message('Hello from clock.js')
    message.destinationName = 'clock'
    mqtt.send(message)
}

mqtt_connect()


function startTime() {
    h = new Date().getHours()
//  f = (h < 8 || h > 22) ? 'h:mm' :  'h:mm:ss'
    f =                     'h:mm';
    t = moment().format(f)
    document.getElementById('clock').innerHTML = t
    t=setTimeout('startTime()', 1000)
}

startTime();


