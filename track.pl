
=begin comment

Track location data sent from phone via tasker

  http://ip_address:8080/bin/track.pl?hb_cell_%LOC_%LOCACC
  http://ip_address:8080/bin/track.pl?bbw_cell_%LOC_%LOCACC

Needs the location.pl code for location_* functions

=cut

use strict;
$^W = 0;                        # Avoid redefined sub msgs

my (@parms) = @ARGV;

return &track(@parms);

sub track {

    my ($data) = "@_";

    my ($who, $how, $where) = $data =~ /(\S+?)_(\S+?)_(\S+)/;

    my ($y, $x, $a) = $where =~ /(\S+),(\S+)_(\S+)/;

    $who = "Helen" if $who eq 'hb';
    $who = "Bruce" if $who eq 'bbw';

    my $loc = &location_check2($who, $x, $y, $a);
    $loc = $where unless $loc;

#   print "\ndb w=$who h=$how loc=$loc xy=$x,$y a=$a d=$data\n";
    logit "$config_parms{data_dir}/logs/location.$Year.$Month.log", "w=$who, h=$how, w=$where, xy=$x,$y a=$a, d=$data, loc=$loc\n";
  
    return &html_page('', 'done');

}
