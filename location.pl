
# Track cell phone locations.  
#   New: Call function location_check2 with x,y via web/bin/track.pl, which is called by phone using Android Tasker

# Category = Location

use vars qw(@location_data);

$get_loc1 = new Voice_Cmd 'Where is [Bruce,Helen,guy1]';
if ($state = said $get_loc1) {
#   my $w = &location_check($state, 1);
    my $w = $Save{"loc_where_$state"};
    $w = 'unknown' unless $w;
    speak "$state is $w" if $w;
}

$display_loc1 = new Voice_Cmd 'Display where is [Bruce,Helen,guy1] log';
if ($state = said $display_loc1) {
    display "$config_parms{data_dir}/logs/location.$Year.$state.log.html";
}

# Verify phone is on
if (new_minute 30) {
    for my $who ('Bruce', 'Helen') {
	my $td1 = $Time - $Save{"loc_when_$who"};
	my $td2 = time_diff($Time, $Save{"loc_when_$who"});  # This will round to nearest min, hour, day, etc
	if ($td1 > 60*15) {
	    speak "Notice, ${who}'s phone has been off for $td2";
	}
    }
}

sub location_check2 {
    my ($who, $x, $y, $a) = @_;
    return unless $x;
    return if $a > 10000 or $x == 0;		# Ignore inaccurate readings

    my $loc1 = "$y $x";
    $Save{"loc_$who"} = $loc1 unless $Save{"loc_$who"};
    $Save{"loc_when_$who"} = $Time;
    
    my $force = 1;
    if ($force or $loc1 ne $Save{"loc_$who"}) {
	@location_data = file_read "$config_parms{data_dir}/logs/location.data" unless @location_data;

	my $d1 = 99999;
	my ($where, $dir);
	for my $data (@location_data) {
	    my ($loc2, $place) = $data =~ /^ *(\S+ +\S+) +(.+?) *\r?$/;
	    my $d2 = &location_distance($loc1, $loc2);
	    if ($d2 < $d1) {
		$d1 = $d2;
		$where = $place;
		$dir = &location_direction($loc1, $loc2);
	    }
	}

	return 'unknown' if $where =~ /ignore/i;  # These are likely false readings.

	my $d_round;
	$d_round = 0.2;
	$d_round = 0.4 if $where =~ /university/i;
	$d_round = 0.3 if $where =~ /home/i;
#	print "db dr=$d_round w=$where\n";
	$where = ($d1 < $d_round) ? "at $where" : "$d1 miles $dir of $where";

	    if ($d1 < 20000 and $where ne $Save{"loc_where_$who"}) {
		speak "$who is $where" if $Save{"loc_where_$who"};
		logit "$config_parms{data_dir}/logs/location.$Year.$who.log", sprintf("%12.7f %12.7f %5d %5.1f %s %s\n", $y, $x, $a, $d1, "https://www.google.com/maps?q=$y+$x&t=m&z=16", $where);
		logit "$config_parms{data_dir}/logs/location.$Year.$who.log.html", "<a href=https://www.google.com/maps?q=$y+$x&t=m&z=16>$where</a><br>\n", 1, 1;
		if ($who eq 'Helen' and $Save{"loc_where_Bruce"} and $Save{"loc_where_Bruce"} ne 'at Home') {	
		    my $url = "https://www.google.com/maps?q=$y+$x&t=m&z=16<br>\nhttp://maps.google.com/maps?daddr=$y+$x";
		    print "location.pl sending mail for $who is $where\n";
#		    net_mail_send account => 'bruce', subject => 'Helen Location', text    => "$who is $where $url";
		}
		
	}
	$Save{"loc_$who"} = $loc1;
	$Save{"loc_where_$who"} = $where;
    }

#   print "db3 w=$who l=$Save{loc_where_$who}, l2=l=$Save{loc_$who}\n";
    return $Save{"loc_where_$who"};
}


# From http://www.meridianworlddata.com/Distance-Calculation.asp
#  Approx: sqrt(x**2 + y**2)   where x = 69.1 * (lat2 - lat1)  y = 53.0 * (lon2 - lon1) 
#  Better: sqrt(x**2 + y**2)   where x = 69.1 * (lat2 - lat1)  y = 69.1 * (lon2 - lon1) * cos(lat1/57.3) 
#  Best:  use the Great Circle Distance Formula
# Latitude=y, Longitude=x (e.g. SLC is +40,-111)


sub location_distance {
    my ($l1, $l2) = @_;
    my ($lat1, $lon1) = split ' ', $l1;
    my ($lat2, $lon2) = split ' ', $l2;

    my $x = 69.1 * ($lat2 - $lat1);
    my $y = 69.1 * ($lon2 - $lon1) * cos($lat1/57.3);
    my $d = sprintf "%2.1f", ($x**2 + $y**2)**0.5;
    return $d;
}

sub location_direction {
    my ($l1, $l2) = @_;
    my ($lat1, $lon1) = split ' ', $l1;
    my ($lat2, $lon2) = split ' ', $l2;

    my $dir = int(atan2($lon1 - $lon2, $lat1 - $lat2) * 180 / 3.14159265);
    $dir += 360 if $dir < 0;
    $dir = convert_direction $dir;
    return $dir;
}


