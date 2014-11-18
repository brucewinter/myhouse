
# Category = Energy

$house_power       = new Generic_Item;
$house_power_used  = new Generic_Item;
$house_power_dir   = new Generic_Item;
$house_power_solar = new Generic_Item;
$house_power_solar_today = new Generic_Item;
$house_power_min   = new Generic_Item;

$v_get_power1 = new Voice_Cmd 'Get power data';

if (said $v_get_power1 or new_minute 1) {
    my $power = &get_power;
    if ($power) {
	speak "$power watts" if said $v_get_power1;
	if ($New_Day) {
	    set $house_power_min $power;
	    $Save{house_power_mina} = 0;
	    $Save{house_power_minc} = 0;
	}
	set $house_power_min $power if $power < (state $house_power_min);
	if (time_greater_than '1 AM' and $power < (20 + state $house_power_min)) {
	    $Save{house_power_mina} += $power;
	    $Save{house_power_minc}++;
#	    print "db p=$power ma=$Save{house_power_mina} mc=$Save{house_power_minc}\n";
	}
    }
}

    
$v_get_power2 = new Voice_Cmd 'Do a [10,15,20,30,60] second power test';

$power_diff_timer   = new Timer;
if ($temp = said $v_get_power2) {
    &get_power1;
    $Save{power_diff} = 0;
    $Save{power_diff_test} = 1;
    set $power_diff_timer $temp;
}

&get_power1 if expired $power_diff_timer;

$v_get_power3 = new Voice_Cmd 'Check nighttime power usage';

if (said $v_get_power3 or time_now "6:30 AM") {
    my $power_min  = int(state $house_power_min);
    my $power_mina = $Save{house_power_mina};
    my $power_minc = $Save{house_power_minc};
    $power_mina = int($power_mina / $power_minc) if $power_minc;
    my $data = "Power usage min: $power_min   min_avg: $power_mina ($power_minc points)";
    print "$data\n";
    my $state_log  = join "\n", state_log $house_power_min;
    net_mail_send  account => 'bruce', subject => $data, text    => "$data\nlog:\n$state_log\n\n https://xively.com/feeds/1661645997\n";  # debug => 1;
}

$v_get_power4 = new Voice_Cmd 'What is the power usage';

if (said $v_get_power4) {
    my $power       = state $house_power;
    my $power_solar = state $house_power_solar;
    my $power_solar_today = state $house_power_solar_today;
    speak "Using $power watts, generating $power_solar watts.  Generated $power_solar_today watt hours today.";
}

if (state_now $house_power and $Save{power_diff_test}) {
    my $power  = state_now $house_power;
    my $powers = state $house_power_solar;
    if ($Save{power_diff} == 0) {
#	print_log "Starting power is $power watts";
	$Save{power_diff} = $power;
    }
    else {
	$Save{power_diff_test} = 0;
	my $pdiff = $power - $Save{power_diff};
	if ($Save{power_dir_test}) {
	    $Save{power_dir_test} = 0;
	    my $pdir;
	                        # If power measurement is bad, simply use solar generation as a metric, or use prev value
	    if (abs($pdiff) < 10 or abs($pdiff) > 100) {
		if ($powers > 800) {
		    $pdir = -1;
		}
		if ($powers < 100) {
		    $pdir = +1;
		}
		else {
		    $pdir = state $house_power_dir;
		}
	    }
	    else {
		$pdir =  ($pdiff > 0) ? +1 : -1;
	    }
	    set $house_power_dir $pdir;
	    logit "$config_parms{data_dir}/logs/power_dir.$Year.log", "pdir=$pdir pdiff=$pdiff p1=$power p2=$Save{power_diff} ps=$powers";
	    print_log "Power difference is $pdiff watts, pdir=$pdir, p=$power ps=$powers";
	}
	else {
	    speak "Power difference is $pdiff watts";
	}
    }
}



                                # Detect if power is running in our out of the house
run_voice_cmd 'Test power direction', undef, undef, 1 if new_minute 10 and state $house_power_solar > 200;

$v_get_power5 = new Voice_Cmd 'Test power direction';

if (said $v_get_power5) {
    set_with_timer $lava_lamp  ON, 10, OFF;
    run_voice_cmd 'Do a 10 second power test', undef, undef, 1;
    $Save{power_dir_test} = 1;
}

			     # Calculate power used, tricky with solar panels
if (new_minute) {
    my $power1    = state $house_power;
    my $power2    = state $house_power_solar;
    my $power3;
    my $power_dir = state $house_power_dir;
    my $power_dira = &state_avg($house_power_dir, 5);

			     # Not much solar, so must be consuming power
    if ($power2 < 200) {
	$power3 = $power1 + $power2;
    }
                             # Generating more power than use, so power is flowing out of house
    elsif ($power_dira < 0 or $power2 > 2000) {
                             # This can happen on cloudy days when sun peeks thru.  power1 is more up to date than power2 (envoy is 5 min old).  Use prev data.
	if ($power2 < $power1) {
#	    $power3 = $power1;
	    $power3 = state $house_power_used;
	    print_log "Error in power calculation, used=$power1 solar=$power2 prev=$power3";
#	    run_voice_cmd 'Test power direction', undef, undef, 1;
	}
	else {
	    $power3 = $power2 - $power1;
	}
    }
    else {
	$power3 = $power1 + $power2;  # Using more power used than generated, power is flowing into house
    }
    set $house_power_used $power3;
    logit "$config_parms{data_dir}/logs/power.$Year.$Month.log", "pd=$power_dir,$power_dira pw=$power1 ps=$power2 pu=$power3";
}


$p_get_power1 = new Process_Item("curl -s 'http://www.wattvision.com/api/download/latest?h=1590801&k=$config_parms{wattvision_key}&v=0.1' > $config_parms{data_dir}/web/get_power1.txt");
$p_get_power2 = new Process_Item("curl -s 'http://192.168.0.142/api/v1/production' > $config_parms{data_dir}/web/get_power2.txt");

sub get_power {
    start $p_get_power1 unless $Save{power_dir_test};
    start $p_get_power2;
    return state $house_power;  # this is old data :(
}
sub get_power1 {
    start $p_get_power1 if done $p_get_power1;
}

my $power_ptime_prev;

if (done_now $p_get_power1) {
    my $data = file_read "$config_parms{data_dir}/web/get_power1.txt";
# [1304287535, 1392, 11]
    $data =~ s/[\[\]]//g;
    my ($ptime, $power, $cents) = split ',', $data;
#   print_log "db pt=$ptime, ptp=$power_ptime_prev, p=$power c=$cents";
    set $house_power $power;
    if (!($Minute % 30) and (!$ptime or $power_ptime_prev eq $ptime)) {
#	print_log "db pt=$ptime, ptp=$power_ptime_prev, p=$power c=$cents";
	speak "Wattvision is down, rebooting";
        set_with_timer $wattvision OFF, 5, ON;
	$power_ptime_prev = 0;
    }
    else {
	$power_ptime_prev = $ptime;
    }
}

if (done_now $p_get_power2) {
    my $data = file_read "$config_parms{data_dir}/web/get_power2.txt";
#  "wattHoursToday": 1913,
#  "wattHoursSevenDays": 139934,
#  "wattHoursLifetime": 291863,
#  "wattsNow": 2271
    $data =~ s/[\n\"\:\{\}\,]//g;
    my @d = split ' ', $data;
    my ($wattsToday, $wattsLife, $wattsNow) = @d[1,5,7];
#   print_log "db power.pl w=$wattsToday, $wattsLife, $wattsNow";
    if ($wattsLife) {
	set $house_power_solar       $wattsNow;
	set $house_power_solar_today $wattsToday;
    }
#   elsif (new_minute 1) {
    elsif (!($Minute % 30)) {
	speak "Enphase Envoy is down, rebooting";
        set_with_timer $wattvision OFF, 5, ON;
    }
}
