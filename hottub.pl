
# Category = Outside

# Turn solar hottub pump on/off, depending on how much sun our solar panels say we have.

$hottub_timer   = new Timer;
    
if (new_minute 1 and ((state $hottub_relay1 == 1) or (time_greater_than("$Time_Sunrise + 2:00") and time_less_than("$Time_Sunset - 3:00")))) {
    my $pump = state $hottub_relay1;
    my $t1  =   state $hottub_temptube;
    my $t2  =   state $hottub_tempinlet;
    my $t3  =   state $hottub_temptub;
#   my $t2a =   &state_avg($hottub_tempinlet);
#   my $t3a =   &state_avg($hottub_temptub);
    my $power_solar = state $house_power_solar;
    my $td12 = $t1 - $t2;
    my $td13 = $t1 - $t3;
    my $td23  = $t2 - $t3;
#   my $td23a = $t2a - $t3a;
    my $td23a = &state_avg($hottub_tdinlet);
#   print_log "Hot Tub data 1: ht p=$pump solar=$power_solar t1=$t1 t2=$t2 t3=$t3 td12=$td12 td13=$td13 td23=$td23,$td23a sunrise=$Time_Sunrise";
    $t3 = round $t3, 0;
# Turn off if tub is too hot, turn on if tubs get too hot
#   if ($pump == 0 and ($t3 < 101 or $t2 > 160)) {
    if (!$pump) {
#	if ($t3 < 102 and $td13 > 10.0) {
#	if ($t3 < 100 and $td23 > 2.0) {
	if ($t3 < 100 and $power_solar > 2000 and inactive $hottub_timer) {
	    speak "Pump on, $t3";
#	    speak "HotTub Pump on, temp $t3";
	    set $hottub_timer 15*60;
	    run_voice_cmd 'Turn hottub pump on';
	}
# With the power_solar data from the solar array, we no longer need this to know if it is sunny.
# Pulse the pump so we have water in the pipes that can steam up when the sun is bright enough, so we measuring td23 works.
#	elsif (time_now "$Time_Sunrise + 3:30" or time_now "$Time_Sunrise + 4:00" or time_now "$Time_Sunrise + 4:30" or time_now "$Time_Sunrise + 5:00") {
#	    run_voice_cmd "Turn hottub pump on";
#	    set $hottub_timer 15*60;
#	}
    }
    else {
#	if ($t3 > 103 and $t2 < 130) {
	if ($t3 > 100) {
	    speak "HotTub Pump too hot, turning off at $t3";
	    run_voice_cmd 'Turn hottub pump off';
	}
	elsif (new_minute 10 and $td23a < 0.5 and inactive $hottub_timer) {
	    speak "Pump off. $t3";
#	    speak "HotTub Pump off. temp $t3";
	    run_voice_cmd 'Turn hottub pump off';
	    set $hottub_timer 15*60;
 	}
    }
}
  
#un_voice_cmd 'Turn hottub pump off' if expired $hottub_timer;
run_voice_cmd 'Turn hottub pump off' if time_now $Time_Sunset;  # make sure it is off at night

sub state_avg {
    my ($item) = @_;
    my @states = state_log $item;
    map(s/.+ [AP]M +(\S+) .+/$1/, @states);  # Drop date/time
    my $avg;
    for my $i (0 .. 9) {
	$avg += $states[$i];
    }
    $avg /= 10;
    return $avg;
}

sub state_prev {
    my ($item) = @_;
    my @states = state_log $item;
    map(s/.+ [AP]M +(\S+) .+/$1/, @states);  # Drop date/time
    return $states[1];  # [0] is current value
}
