import pytest
import os
import logging
import shutil
from wgd.core import SequenceData, get_gene_families, KsDistributionBuilder

# some config: set logging level, and get directory
logging.basicConfig(level=logging.ERROR)
thisdir = os.path.dirname(os.path.abspath(__file__))


# Not sure how to structure exactly...
class TestSeqData:
    @pytest.fixture
    def data(self):
        datadir = os.path.join(thisdir, "data")
        s1 = os.path.join(datadir, "ugi1000.fasta")
        s2 = os.path.join(datadir, "egu1000.fasta")
        return (s1, s2)

    def test_seqio(self, tmpdir, data):
        s1, s2 = data
        logging.info("Testing `SequenceData` (IO)")
        d0 = SequenceData(s1, out_path=tmpdir, tmp_path=tmpdir, cds=True, to_stop=True)
        d1 = SequenceData(s1, out_path=tmpdir, tmp_path=tmpdir, cds=False, to_stop=False)
        d2 = SequenceData(s2, out_path=tmpdir, tmp_path=tmpdir, cds=False, to_stop=False)
        assert len(d0.cds_seqs) == 224  # Should only read proper CDS
        assert len(d1.cds_seqs) == 500  # Should read full file
        assert len(d2.pro_seqs) == 500  # Proper translation

    def test_paranome(self, data, tmpdir):
        logging.info("Testing paranome (requires diamond+mcl)")
        s1, s2 = data
        d = SequenceData(s1, out_path=tmpdir, tmp_path=tmpdir, cds=False, to_stop=True)
        d.get_paranome()
        assert len(d.mcl) == 35  # Got the paranome

        # round tripping for families?
        # write to file/read from file
        families = d.write_paranome()
        with open(families, "r") as f:
            fams = [x.strip().split("\t") for x in f.readlines()]
        fams = get_gene_families(d, fams)
        assert len(d.mcl) == len(fams)  # Round tripped

        # construct gene families directly from `self.mcl`
        fams2 = get_gene_families(d, d.mcl.values(), rename=False)
        assert len(fams2) == len(fams)

    def test_rbh(self, data, tmpdir):
        logging.info("Testing RBH orthologs (requires diamond)")
        s1, s2 = data
        d1 = SequenceData(s1, out_path=tmpdir, tmp_path=tmpdir, cds=False, to_stop=False)
        d2 = SequenceData(s2, out_path=tmpdir, tmp_path=tmpdir, cds=False, to_stop=False)
        d1.get_rbh_orthologs(d2, eval=1e-3)
        df = d1.rbh[d2.prefix]
        assert len(df.index) == 19  # Got all RBHs
        assert len(df.columns) == 12  # Right No. columns

    def test_ksd(self, data, tmpdir):
        s1, s2 = data
        d = SequenceData(s1, out_path=tmpdir, tmp_path=tmpdir, cds=True, to_stop=True)
        d.get_paranome()

        # alignment without gap-stripping
        fams = get_gene_families(d, d.mcl.values(), rename=False, 
                prequal=False, strip_gaps=False)
        f = fams[0]
        f.align()
        cds_len = f.cds_aln.get_alignment_length()
        pro_len = f.pro_aln.get_alignment_length()
        assert cds_len == 558  # Alignment working?
        assert cds_len == 3*pro_len  # "AA -> codon fine?

        # alignment with gap-stripping
        fams = get_gene_families(d, d.mcl.values(), rename=False,
                prequal=False, strip_gaps=True)
        f = fams[0]
        f.align()
        cds_len = f.cds_aln.get_alignment_length()
        pro_len = f.pro_aln.get_alignment_length()
        gaps = 0
        for i in range(pro_len):
            if "-" in f.pro_aln[:,i]:
                gaps += 1
        assert cds_len == 3*(pro_len - gaps)

    #    # Codeml

    #    # Tree inference

    #    # run Ks distribution construction
    #    #ksdb = KsDistributionBuilder(fams)
    #    #ksdb.get_distribution()



