var input_box = document.getElementById("input_box");
var chat_out = document.getElementById("area_log");
var action_out = document.getElementById("action_log");
var channels = false;

const wsstring = wsurl +"?"+ csessid;
var socket = new WebSocket(wsstring);
var pingInterval;

window.addEventListener("unload", function(ev) {
	if (channels) channels.close();
}, false);

function toggleTheme(e) {
	if (e.checked) {
		document.documentElement.setAttribute('data-theme', 'dark');
		localStorage.theme = "dark";
	}
	else {
		document.documentElement.setAttribute('data-theme', 'light');
		localStorage.theme = "light";
	}
}

function MakeClickables(el) {
	for (var i = 0; i < el.childNodes.length; i++) {
		curr = el.childNodes[i];
		if (curr.nodeType != 1) continue;
		if (curr.classList.contains("mxplink")) {
			curr.addEventListener("click", mxp_send);
    }        
		MakeClickables(curr);
	}
}

function LogTo(el, msg, cls) {
	if (msg) {
		console.log("received", msg);
		msg_div = '<div class="'+cls+'">'+msg+'</div>';
		el.insertAdjacentHTML("beforeend",msg_div);
		MakeClickables(el.lastChild);
		el.scrollTop = el.scrollHeight;
	}
	else console.log("received empty message");
}

function LogClear(el) {
	el.innerHTML = "";
}

function PopChannels() {
	if (!channels || channels.closed) {
		channels = window.open("channels","","width=500,height=400,popup");
		channels.addEventListener("load", function(ev) {
			var channel_input = channels.document.getElementById('input_box');
			channel_input.addEventListener("keydown", function(ev) {
				if (ev.key == 'Enter' && !ev.shiftKey) {
					ev.preventDefault();
					var message = channel_input.value;
					var channid = channel_input.dataset.channel
			
					if (String(message).length && channid.length) {
						message = channid + " " + message;
						SendFunc('text', message, '');
						channel_input.value = "";
					}
				}
			}, false);
			SendFunc('get_channels', '', {});
		}, false);
	}
	channels.focus();
}

/* add a new message to the chat window */
function EmoteAdd(message, mtype) {
	cls = "message";
	if (mtype) cls += " "+mtype;
	LogTo(chat_out,message,cls);
}

function ActionAdd(message) {
	LogTo(action_out,message,"action");
}

function ServerMsg(message) {
	LogTo(action_out, message, "system")
}
function ChannelMsg(message, channid) {
	if (channels && !channels.closed) {
		var chan_elem = channels.document.getElementById(channid + "_log");
		if (!chan_elem) {
			chan_elem = channels.addChannel(channid);
		}
		LogTo(chan_elem,message,"message");
	}
}

function SetModal(content) {
	closer_elem = document.getElementById('closer_div');
	if (!closer_elem) {
		// create the div
		closer_elem = document.createElement('div');
		closer_elem.id = 'closer_div';
		closer_elem.addEventListener('click', CloseModal);
		document.body.append(closer_elem);
	}
	menu_elem = document.getElementById('modal_div');
	if (!menu_elem) {
		// create the popup
		menu_elem = document.createElement('div');
		menu_elem.id = 'modal_div';
		document.body.append(menu_elem);
	}
	menu_elem.innerHTML = content;
	MakeClickables(menu_elem)
}

function CloseModal(ev) {
	send_quit = false;
	el = document.getElementById('closer_div');
	if (el) {
		el.remove();
		send_quit = true;
	}
	el = document.getElementById('modal_div');
	if (el) {
		el.remove();
		send_quit = true;
	}
	if (send_quit) SendFunc('close_quit', '', '');
}

function SetHTML(id, content) {
	el = document.getElementById(id);
	el.innerHTML = content;
	MakeClickables(el);
}
function ChangeLocation(message) {
//	LogClear(chat_out);
	SetHTML("area", message);
}
function UpdatePrompt(message) {
	SetHTML("prompt", message);
}
function LookAt(message) {
	SetHTML("look", message);
}

function SendFunc(func, args, kwargs) {
	data = [func, args, kwargs];
	if (socket.readyState === WebSocket.CLOSED) {
		ServerMsg("Server not connected - command not sent.")
	}
	else {
		console.log("sending",data);
		socket.send(JSON.stringify(data));
	}
}

// function to navigate back and forward through the tab's session input history
function NavCmdHistory(el, store_key, direction) {
	var store_item = sessionStorage.getItem(store_key);
	if (!store_item) return;
	store_item = JSON.parse(store_item);
	var index = el.dataset.cmd_index;
	if (!index) {
		// assume we're at the end
		index = store_item.length;
		if (el.value) {
			store_item.push(el.value);
			LogSessionCmd(store_key, el.value);
		}
	}
	else index = Number(index);
	index += direction;
	if ((index < store_item.length) && (index >= 0)) {
		el.value = store_item[index];
		el.dataset.cmd_index = index;
	}
}
// function to add an input to the session input history
function LogSessionCmd(store_key, message) {
	var store_item = sessionStorage.getItem(store_key);
	if (store_item) {
		store_item = JSON.parse(store_item);
		store_item.push(message);
	}
	else {
		store_item = [ message ];
	}
	sessionStorage.setItem(store_key, JSON.stringify(store_item));
}
// various input-handling functions
function HandleText(message, opts) {
	if (opts.clear) {
		LogClear(chat_out);
		LookAt('');
	}
	var sent = false;
	switch (opts.target) {
		case "location":
			ChangeLocation(message);
			sent = true;
			break;
		case "modal":
			SetModal(message);
			sent = true;
			break;
		case "look":
			LookAt(message);
			sent = true;
			break;
		case "emote":
			EmoteAdd(message);
			sent = true;
			break;
		case "channels":
			ChannelMsg(message, opts.from_channel);
			sent = true;
			return;
	}

	switch (opts.type) {
		case 'move':
		case 'weather':
			SendFunc('auto_look', '', {});
			break;
		case 'system':
			ServerMsg(message);
			break;
		case 'menu':
			SetModal(message);
			break;
		case 'help':
			SetModal(message);
			break;
		case 'look':
			LookAt(message);
			break;
		default:
			if (!sent) ActionAdd(message);
	}
}

socket.onopen = function (e) {
	pingInterval = setInterval(function(){
		// this is a totally fake stupid ping because everything is stupid
		data = ['ping', 'ping', ''];
		socket.send(JSON.stringify(data));
	}, 45000);
}
socket.onclose = function (e) {
	console.log(e.code);
	if (e.code != 1001) {
		if (e.reason) ServerMsg("Connection closed: "+e.reason+"\n");
		else ServerMsg("Connection closed.");
	}
	clearInterval(pingInterval)
};

socket.onerror = function (e) {
	ServerMsg("Connection error.");
	console.log(e);
};

socket.onmessage = function (e) {
	msg = JSON.parse(e.data);
	switch (msg[0]) {
		case 'text':
			HandleText(msg[1][0], msg[2]);
			break;
		case 'prompt':
			UpdatePrompt(msg[1][0]);
			break;
		case 'chaninfo':
			if (channels) channels.addChannel(msg[1][0]);
			break;
		default:
			console.log(msg);
	}
};

/* post handler */
input_box.addEventListener("keydown", function(ev) {
	// might do something fancy with this for myself later
	log_store_key = "gameinput"
	if (ev.key == 'Enter' && !ev.shiftKey) {
		ev.preventDefault();
		var message = input_box.value;

		if (String(message).length) {
			LogSessionCmd(log_store_key, message);
			input_box.value = "";
			LogTo(action_out, "> "+message, 'cmd');
			SendFunc('text', message, '');
			if (input_box.dataset.cmd_index) delete input_box.dataset.cmd_index;
		}
	}
	else if (ev.key == 'ArrowUp') {
		// only go back through the history if the cursor is at the beginning
		if (this.selectionStart === 0) {
			NavCmdHistory(this, log_store_key, -1);
		}
	}
	else if (ev.key == 'ArrowDown') {
		// only go forward through the history if the cursor is at the end
		if (this.selectionEnd === this.value.length) {
			NavCmdHistory(this, log_store_key, 1);
		}
	}
}, false);

function mxp_send(ev) {
	if (typeof(this.dataset.command) == 'undefined') return;
	command = this.dataset.command;
	if (ev.ctrlKey || ev.shiftKey) {
		pieces = command.split(" ");
		command = "look "+ pieces.slice(1).join(" ");
	}
	SendFunc('text', command, '');
}

document.addEventListener("paste", (e) => {
	if (input_box !== document.activeElement) input_box.focus();
});

document.addEventListener("keydown", (e) => {
	if (e.key === 'Escape' && input_box === document.activeElement) input_box.blur();
	if (document.getElementById('closer_div')) {
		if (e.key === 'Escape') CloseModal(e);
		// TODO: make it so i can enter a number key on the modal to choose an option
	}
	if (input_box !== document.activeElement) {
		if (e.key && e.key.length === 1 && !(e.ctrlKey || e.altKey)) {
			input_box.focus();
		}
	}
});
