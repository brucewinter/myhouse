#!/usr/bin/perl

# Create a video from the last x $hours of images from $dir
# Called from ss_monitor_review.  An example call:
#   ~/bin/ss_s2v.pl 5 /mnt/home/temp/is.b  out.mp4

use strict;

my $hours = shift;
my $dir   = shift;
my $out   = shift;

my $tdir = "/home/bruce/temp/sv";

system "rm $tdir/*";
    
print "ss_sv2.pl copying files from the last $hours hours from $dir into $out\n";

opendir (DIR, $dir);
my @dir=readdir(DIR);
closedir(DIR);
my $i = 0;
for my $m (sort { -M "$dir/$a" <=> -M "$dir/$b" } @dir ) {
    next unless $m =~ /jpg/;
    my ($ftime) = (stat("$dir/$m"))[9];
    last if (time - $ftime) > 3600 * $hours;
#   print "$dir/$m\n";
    my $i2 = sprintf "%03d", $i++;
    system "cp '$dir/$m' $tdir/img_$i2.jpg";
}

print "ss_sv2.pl running ffmpeg\n";

system "ffmpeg -y -framerate 3 -i $tdir/img_%03d.jpg -r 30 $out  > /dev/null 2>&1";

print "ss_sv2.pl done, $out created.\n";
