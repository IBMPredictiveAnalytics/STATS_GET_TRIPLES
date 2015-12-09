file handle data /name="c:\cc\misc2\extensions\python\stats_get_triples\tests".

begin program.
import STATS_GET_TRIPLES
reload(STATS_GET_TRIPLES)
end program.

* fixed format file.
STATS GET TRIPLES METADATA="data\example1.sss" syntax="data\example1.sps" execute=yes.

* csv file.
STATS GET TRIPLES METADATA="data\example2.sss" syntax="data\example2.sps".


STATS GET TRIPLES METADATA="C:\cc\misc2\extensions\python\STATS_GET_TRIPLES\tests\example1.sss" 
    DATA="C:\cc\misc2\extensions\python\STATS_GET_TRIPLES\tests\example1.txt" 
    SYNTAX="c:\temp\example1test.sps"
EXECUTE=YES.


STATS GET TRIPLES METADATA="C:\cc\misc2\extensions\python\STATS_GET_TRIPLES\tests\example1.sss" 
    DATA="C:\cc\misc2\extensions\python\STATS_GET_TRIPLES\tests\example1.txt" 
    SYNTAX="c:\temp\example1test.sps" EXECUTE=YES
    /options removehtml=yes fulllabelattr=yes mdvallabels='zero' 'one'.


STATS GET TRIPLES METADATA="C:\cc\misc2\extensions\python\STATS_GET_TRIPLES\tests\example2.sss" 
    DATA="C:\cc\misc2\extensions\python\STATS_GET_TRIPLES\tests\example2.txt" 
    SYNTAX="c:\temp\example2test.sps"  EXECUTE=YES
    /options removehtml=yes fulllabelattr=yes mdvallabels='zero' 'one'.



execute.
