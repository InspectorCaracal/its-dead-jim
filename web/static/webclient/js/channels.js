function addChannel(channid) {
	var curr_chan = document.getElementById('input_box').dataset.channel
	if (!document.getElementById(channid+"_log")) {
		new_log = document.createElement('div');
		new_log.id = channid + "_log";
		if (!curr_chan) {
			document.getElementById('input_box').dataset.channel = channid;
		}
		else {
			new_log.classList.add("invisible");
		}
		document.getElementById('channel_log').append(new_log);
	}
	if (!document.getElementById(channid+"_tab")) {
		new_tab = document.createElement('span');
		new_tab.id = channid + "_tab";
		new_tab.dataset.channel = channid;
		new_tab.classList.add("chan-tab");
		new_tab.innerText = channid;
		new_tab.addEventListener("click", swapChannel, false);
		document.getElementById('channel_tabs').append(new_tab);
		if (!curr_chan) {
			new_tab.classList.add("active-tab");
		}
	}
}

function swapChannel(ev) {
	channid = this.dataset.channel;
	if (!channid)	return;
	new_log = document.getElementById(channid + "_log");
	if (!new_log) {
		new_log = document.createElement('div');
		new_log.id = channid + "_log";
		document.getElementById('channel_log').append(new_log);
	}
	else {
		new_log.classList.remove("invisible");
	}
	curr_chan = document.getElementById('input_box').dataset.channel;
	if (curr_chan) {
		curr_log = document.getElementById(curr_chan + "_log");
		if (curr_log) {
			curr_log.classList.add('invisible');
		}
		curr_tab = document.getElementById(curr_chan + "_tab");
		if (curr_tab) {
			curr_tab.classList.remove('active-tab');
		}
	}
	this.classList.add('active-tab');

	document.getElementById('input_box').dataset.channel = channid;
}