
# Example of Villin NLE double mutant folding analysis with PLUMED2
# collective variables. Follows roughly the protein folding tutorial
# at https://www.htmd.org/docs/latest/userguide/analysing.html , but
# here we shall use PLUMED CVs.  Please download and extract the
# villin trajectories dataset from the URL above.

# For the sake of illustration, we shall reproduce some of the CVs in
# Giorgino T, Laio A, Rodriguez A. METAGUI 3: A graphical user
# interface for choosing the collective variables in molecular
# dynamics simulations. Computer Physics
# Communications. 2017;217:204–9.  doi:10.1016/j.cpc.2017.04.009

# First, install HTMD according to the instructions. To use the latest
# version, clone from https://github.com/Acellera/htmd and prepend the
# directory to PYTHONPATH. Note that as of June 2017 the features are
# under development in the "toni-devel-plumed" branch, which will be
# merged later.

# In the unlikely case that  plumed 2 is not in path
# import os
# os.environ["PATH"]="/usr/local/bin:/Users/toni/bin:"+os.environ["PATH"]


# Import HTMD
from htmd import *

# Until this is merged in master
from htmd.projections.metricplumed2 import *

# This is just to check if and where PLUMED2 is found.
htmd.projections.metricplumed2._getPlumedRoot()

# The PDB corresponding to the structure
m=Molecule("villin/datasets/1/filtered/filtered.pdb")

# Extract the carbon-alpha atoms only
mca=m.copy()
mca.filter("name CA")


## --------------------------------------- 

# Radius of gyration CV. This is easy.
rg=PlumedCV("GYRATION",ATOMS=mca,label="rg")


## --------------------------------------- 

# Now compute the content of alpha-helix. For PLUMED's MOLINFO to
# recognize the residues, we should rename NLE as LEU, and OT1 as
# O. This is performed easily, but we work on a copy of the protein.

m_no_nle = m.copy()             # Work on a copy
m_no_nle.set('resname','LEU','resname NLE')      # set resname<-LEU where resname==NLE
m_no_nle.set('name','O','resid 76 and name OT1') # set name   <-O   where resid==76 and name==OT1
molinfo = PlumedMolinfo(m_no_nle)                # Output the MOLINFO statement

# Build the ALPHARMSD statement
armsd=PlumedCV("ALPHARMSD",RESIDUES="42-76", R_0="1.0", label="armsd")


## --------------------------------------- 

# Number of hydrophobic contacts - i.e. coordination number (at 3.5 A) of
# heavy atoms in the sidechains of hydrophobic residues.

# First, get which residues are hydrophobic (there are 17, including 2
# norleucines)
hydrophobic_resnames = ["ALA","VAL","ILE","LEU","MET","PHE","TYR","TRP","NLE"]
hyd=numpy.in1d(mca.resname,hydrophobic_resnames)
hyd_resid=mca.resid[hyd]

# Each of the sidechains gets its own group: hg_1 to hg_17
pg=[]
for resid in hyd_resid:
    pg.append(PlumedGroup(m,
                          "hg_{}".format(len(pg)),
                          "resid {} and not name N CA C O and noh".format(resid)))

ngroups=len(pg)

# Form COORDINATION CVs between all the pairs. There are 17*16/2=136 pairs. 
group_pairs=[]
for g1 in range(ngroups):
    for g2 in range(g1+1,ngroups):
        group_pairs.append(PlumedCV("COORDINATION",
                                    GROUPA=pg[g1],
                                    GROUPB=pg[g2],
                                    R_0="3.5",
                                    label="c_{}".format(len(group_pairs)+1)))

# Now form the final CV, called "hbc", summing all of the contacts counted above.
hydrophobic_contacts_sum = PlumedCV("COMBINE", ARG=group_pairs, PERIODIC="NO", label="hbc")
tmp2=MetricPlumed2(hydrophobic_contacts_sum)

# Used to debug the topological sort algorithm ---
#  tmp=htmd.projections.metricplumed2._printDFS(hydrophobic_contacts_sum)
#  print("\n".join(tmp))



## --------------------------------------- 

# The metric is now the composition of the 3 CVs + MOLINFO + their dependencies

villin_cvs=MetricPlumed2([molinfo,armsd,rg,hydrophobic_contacts_sum])

print(villin_cvs)

## --------------------------------------- 


# Now build the simulation list and compute the metrics over it
sets = glob('villin/datasets/*/')
sims = []
for s in sets:
    fsims = simlist(glob(s + '/filtered/*/'), 'villin/datasets/1/filtered/filtered.pdb')
    sims = simmerge(sims, fsims)

# Create a new Metric on the trajectories
metr = Metric(sims)

# Connect it to the CVs defined
metr.set(villin_cvs)

# Evaluate - the 3 GB take approx 10 min on a MacBook 2016
data = metr.project()

# frame interval in ns
data.fstep=.1                   

# Save
data.save("villin_data.save")


# Note the shape!  data.dat contains the trajectories
print("Trajectories: "+str(data.dat.shape))

# Each data.dat[i] contains trajectory i, an array 500x139
# 500 are the timesteps for that trajectory
# 139 are the 136 COORDINATION + 1 COMBINE + 1 GYRATION + 1 ALPHARMSD
print("Shape of trajectory 0: "+str(data.dat[0].shape))



## --------------------------------------- 

# Drop trajectories whose length is not mode
data.dropTraj()
data.dat.shape

# Only keep the final 3 CVs (delete COORDINATION) - this will be more
# automated in the future.
last3CV=[136,137,138]

# Bug: gives error, but works
try:
    data.dropDimensions(keep=last3CV)
except:
    pass




## --------------------------------------- 

# We may do TICA here. Let's not.
#  tica = TICA(data,2,units='ns')
#  dataTica = tica.project(2)

# We may bootstrap here. Let's not.



## --------------------------------------- 

# Cluster
data.cluster(MiniBatchKMeans(n_clusters=1000))

# Build Markov Model
model=Model(data)

# The thrill starts here.  Check implied timescales' convergence.
model.plotTimescales()




