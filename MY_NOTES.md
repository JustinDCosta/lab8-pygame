(earlier related notes would be in the report as i wasnt sure if i should do it just in report or on both report and notes. from now on i will do them separately.)

LAB 11(CHASING):
Since we already have the flee feature, we already know that the smaller circle will run from the bigger circle. But here we know that the bigger circle doesn't follow the the small circle. All we need to do is make the bigger circle follow the smaller one. BUT the issue that is comming to my mind is which one will it follow, when there are multiple around it and also in different sizes, which one is it supposed to chase. 

OKay, so the bigger circle will chase the closest smaller circle within a chase radius(so that needs to be specific, since i have 3 sizes medium will have a specific chase radius and the big one would have its own chase radius(slightly bigger than the medium one)). But what if 2 or more smaller circles are at the exactly same distance closest to the bigger ones. I need to make it so that in that case, the bigger circle will chase the medium one as the medium one would chase the smaller one. and in case of multiple of the same sizes, the bigger circle randomly will choose one of them.

So, i will need to define the chase radius for the circles. make a function where the big chases the small ones.

****************
23-Apr-2026 11:06am
Redid most of the stuff, so as to make it more simpler and human readable code. since i was using AI from the start more most of the stuff, some of the code got a bit complicated for me to understand, therefore i went through it again. I have added all the features that were requested, and also have comments for me to understand what the code is about(making it easier to navigate back and forth). Will be going through this again next week to see if i can add any new features or polish it further.
