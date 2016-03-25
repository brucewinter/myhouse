
# Category = Energy

# Reads power meter data using rtlamr rf reader
#  - rtlamr software by Douglass Hall, available here: https://github.com/bemasher/rtlamr
#  - rtlsdr USB radios available here: http://www.amazon.com/gp/product/B00JQZU1ZO

$RTLAMR = new  main::Socket_Item(undef, undef, 'localhost:5556', 'rtlamr', 'tcp', 'raw');
if ($Startup) {
    print_log "Starting RTLARM server and client";
    system "(/home/bruce/gocode/bin/rtlamr -server 127.0.0.1:5555  | netcat -l 5556)&";  #-filterid 27306567,27306568 
    start $RTLAMR;
}

if ($state = said $RTLAMR) {
# {Time:2014-11-22T14:56:06.636 SCM:{ID:30701294 Type: 8 Tamper:{Phy:01 Enc:00} Consumption:  102714 CRC:0x428F}}
    my ($time, $id, $watts) = $state =~ /Time\:(\S+) .+ID\:(\d+) .+Consumption: *(\d+)/;
    if ($id) {
	$watts *= 10;
	my $ref = $Persistent{power_rf};
	$$ref{$id}{count}++;
	my $time2  = str2time $time;
	my $tdiff = $time2 - $$ref{$id}{time};
	my $pdiff = $watts - $$ref{$id}{watts}{latest} if defined $$ref{$id}{watts};
	my $whour = int(3600 * $pdiff / $tdiff);
#	print_log "db power: t=$time id=$id p=$watts, pdiff=$pdiff, whour=$whour, tdiff=$tdiff, c1=" . $$ref{$id}{count};
                                          # Save data only for active meters, >10 readings in the previous 60 minutes. 
	                                  # Also avoid frequent samples, to smooth out the whour calcualtion.
	if ($tdiff > 90 and $$ref{$id}{ch} > 10) {
#	    print_log "db power: m=$id t=$time2 p=$watts pd=$pdiff td=$tdiff wh=$whour c3=" . $$ref{$id}{ch};
	    $$ref{$id}{pdiff} = $pdiff;
	    $$ref{$id}{tdiff} = $tdiff;
	    $$ref{$id}{whour} = $whour;
	    $$ref{$id}{time}  = $time2;
	    $$ref{$id}{watts}{latest} = $watts;

                                           # Look for my house data, both used in and solar out meters
	    my $house_dir;
	    $house_dir =  'in' if $id eq '27306567';
	    $house_dir = 'out' if $id eq '27306568';
	    $house_dir = 'net' if $id eq '27306569';
	    if ($house_dir) {
		$Save{"house_power_time_"  . $house_dir}  = $time2;
		$Save{"house_power_whour_" . $house_dir}  = $whour;
		$Save{"house_power_dir"} = ($Save{house_power_whour_net} < 0) ? 'out' : 'in';
#		print "db power: p=$whour, hd=$house_dir, in=$Save{house_power_whour_in} out=$Save{house_power_whour_out} dir=$Save{house_power_dir}\n";
	    }
	}
    }
}

$power_house_list = new Voice_Cmd "List house power counts";
if ($New_Day or said $power_house_list) {
    my ($report, $c1, $c2, $c3, $c4);
    $c3 = 9999;
    my $ref = $Persistent{power_rf};
    for my $id (sort keys %$ref) {
	$report .= "$Mday $id $$ref{$id}{cd} $$ref{$id}{ct}\n";
	next unless $$ref{$id}{cd};
	$c1++;
	$c2  = $$ref{$id}{cd} if $$ref{$id}{cd} > $c2;
	$c3  = $$ref{$id}{cd} if $$ref{$id}{cd} < $c3;
	$c4 += $$ref{$id}{cd};
    }
    $c4 = int($c4/$c1);
    $report .= "Total: $c1 houses, min/max/avg count: $c3/$c2/$c4\n";
    file_write "$config_parms{data_dir}/logs/power_rf.counts.Day_$Mday.txt", $report;
    print $report;
}

if ($New_Hour) {
    my $ref = $Persistent{power_rf};
    for my $id (keys %$ref) {
	$$ref{$id}{ch}  = $$ref{$id}{count};
	$$ref{$id}{cd} += $$ref{$id}{count};
	$$ref{$id}{ct} += $$ref{$id}{count};
	$$ref{$id}{count} = 0;
    }
    my $report;
    for my $id (sort keys %$ref) {
	my $w1 = $$ref{$id}{watts}{latest};
	my $w2 = $$ref{$id}{watts}{last_hour};
	next unless defined $w1;
	my $w3 = $w1 - $w2;
	$$ref{$id}{watts}{last_hour}      = $w1;
	$$ref{$id}{watts}{last_hour_used} = $w3;
	$report .= "$Hour $id $w3 $$ref{$id}{ch}\n" if $w2 and $w3;
    }
    logit "$config_parms{data_dir}/logs/power_rf.Day_$Mday.txt", $report, 0;
}
if ($New_Day) {
    my $ref = $Persistent{power_rf};
    my $report;
    for my $id (sort keys %$ref) {
	my $w1 = $$ref{$id}{watts}{latest};
	my $w2 = $$ref{$id}{watts}{last_day};
	next unless defined $w1;
	my $w3 = $w1 - $w2;
	$$ref{$id}{watts}{last_day}      = $w1;
	$$ref{$id}{watts}{last_day_used} = $w3;
	$report .= "$Mday $id $w3 $$ref{$id}{cd}\n" if $w2 and $w3;
	$$ref{$id}{cd} = 0;
    }
    logit "$config_parms{data_dir}/logs/power_rf.Month_$Month.txt", $report, 0;
}
if ($New_Month) {
    my $ref = $Persistent{power_rf};
    my $report;
    for my $id (sort keys %$ref) {
	my $w1 = $$ref{$id}{watts}{latest};
	my $w2 = $$ref{$id}{watts}{last_month};
	next unless defined $w1;
	my $w3 = $w1 - $w2;
	$$ref{$id}{watts}{last_month}      = $w1;
	$$ref{$id}{watts}{last_month_used} = $w3;
	$report .= "$Month $id $w3 $$ref{$id}{ct}\n" if $w2 and $w3;
    }
    logit "$config_parms{data_dir}/logs/power_rf.watts.Month_$Month.txt", $report, 0;
}

                                             # Cleanup xively plots periodially, deleteing plots with bad data

$power_house_list2 = new Voice_Cmd "Reset bad rf power data";
if (said $power_house_list2) {
    my $ref = $Persistent{power_rf};
    for my $id (sort keys %$ref) {
	print "power_rf resetining for id=$id\n";
	`curl --request DELETE --header 'X-ApiKey: $config_parms{xively_key}' 'https://api.xively.com/v2/feeds/1037196380/datastreams/$id/datapoints?start=2014-11-26T03:00:00Z&end=2014-11-26T06:00:00Z'`;
    }
}

$power_house_list3 = new Voice_Cmd "Delete bad rf power meters";
if (said $power_house_list3) {
    my $json = `curl --silent --request GET --header 'X-ApiKey: $config_parms{xively_key}' 'https://api.xively.com/v2/feeds/1037196380.json'`;
    my $p1 = decode_json $json if $json;
    for my $d (@{$$p1{datastreams}}) {
	my $t1 = str2time($$d{at});
	my $t2 = int(($Time - $t1) / 3600);
	my $r = $$d{max_value} - $$d{min_value};
	my $f = 'keep ';
	$f = 'delete' if $t2 > 12 or $r < 50;
	print "$f id=$$d{id} t=$$d{at} t1=$t1 t2=$t2 r=$r v=$$d{current_value},$$d{min_value},$$d{max_value} \n";
	`curl --request DELETE --header 'X-ApiKey: $config_parms{xively_key}' 'https://api.xively.com/v2/feeds/1037196380/datastreams/$$d{id}'` if $f eq 'delete';
    }
}

