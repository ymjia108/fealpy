import numpy as np
from scipy.sparse import coo_matrix, csc_matrix, csr_matrix, spdiags, eye, tril, triu
from scipy.sparse import triu, tril, find, hstack
from .mesh_tools import unique_row

from tvtk.api import tvtk, write_data
class PolyhedronMesh():
    def __init__(self, point, face, faceLocation, face2cell, NC=None, dtype=np.float):
        self.point = point
        self.ds = PolyhedronMeshDataStructure(point.shape[0], face, faceLocation, face2cell, NC=NC)
        self.meshtype = 'polyhedron'
        self.dtype= dtype 

    def to_vtk(self):
        NF = self.number_of_faces()
        face = self.ds.face
        face2cell = self.ds.face2cell
        faceLocation = self.ds.faceLocation
        NV = self.ds.number_of_vertices_of_faces()


        isPoly = (face2cell[:, 0]) == 59 |  (face2cell[:, 1] == 59)
        isBadPoly, V = self.check()
        idx, = np.nonzero(isBadPoly)
        print(V[idx])
        for i in idx:
            isPoly = (face2cell[:, 0] == i)  |  (face2cell[:, 1] == i) 
#        isPoly = isBadPoly[face2cell[:, 0]] | isBadPoly[face2cell[:, 1]]
            NNF = np.sum(isPoly)
            faces = np.zeros(np.sum(NV[isPoly]) + NNF, dtype=np.int)
            isIdx = np.ones(len(faces), dtype=np.bool)
            isIdx[0] = False
            isIdx[np.add.accumulate(NV[isPoly]+1)[:-1]] = False
            faces[~isIdx] = NV[isPoly]
            isPoly = np.repeat(isPoly, NV) 
            faces[isIdx] = face[isPoly]

            ug = tvtk.UnstructuredGrid(points=self.point)
            cell_type = tvtk.Polygon().cell_type
            cell = tvtk.CellArray()
            cell.set_cells(NNF, faces)
            ug.set_cells(cell_type, cell) 
            write_data(ug, str(i)+'.vtk')

        return NNF, faces

#        faces = np.zeros(len(face) + NF, dtype=np.int)
#        isIdx = np.ones(len(face) + NF, dtype=np.bool)
#        isIdx[0] = False
#        isIdx[np.add.accumulate(NV+1)[:-1]] = False
#        faces[~isIdx] = NV
#        faces[isIdx] = face
#        return NF, faces

    def check(self):
        N = self.number_of_points()
        NC = self.number_of_cells()
        NFE = self.ds.number_of_edges_of_faces()
        
        face2cell = self.ds.face2cell
        isIntFace = (face2cell[:, 0] != face2cell[:, 1])

        cell2point = self.ds.cell_to_point()
        V = cell2point@np.ones(N, dtype=np.int)
        E = np.zeros(NC, dtype=np.int)
        F = np.zeros(NC, dtype=np.int)

        np.add.at(E, face2cell[:, 0], NFE)
        np.add.at(E, face2cell[isIntFace, 1], NFE[isIntFace])
        print("Polygon test:")
        print(NFE[(face2cell[:, 0] == 36) & (face2cell[:, 1] != 36)])
        print(NFE[(face2cell[:, 0] != 36) & (face2cell[:, 1] == 36)])
        print(np.nonzero((face2cell[:, 0] == 36) & (face2cell[:, 1] != 36)))
        print(np.nonzero((face2cell[:, 0] != 36) & (face2cell[:, 1] == 36)))
        E = E//2

        np.add.at(F, face2cell[:, 0], 1)
        np.add.at(F, face2cell[isIntFace, 1], 1)

        val = F - E + V 
        isBadPoly = (val != 2)
        print(isBadPoly.sum())
        return isBadPoly, V 
    def number_of_points(self):
        return self.point.shape[0]

    def number_of_edges(self):
        return self.ds.NE

    def number_of_faces(self):
        return self.ds.NF

    def number_of_cells(self):
        return self.ds.NC

    def geom_dimension(self):
        return self.point.shape[1]

    def face_angle(self):
        point = self.point
        face = self.ds.face
        faceLocation = self.ds.faceLocation

        idx1 = np.zeros(face.shape[0], dtype=np.int)
        idx2 = np.zeros(face.shape[0], dtype=np.int)

        idx1[0:-1] = face[1:]
        idx1[faceLocation[1:]-1] = face[faceLocation[:-1]]
        idx2[1:] = face[0:-1]
        idx2[faceLocation[:-1]] = face[faceLocation[1:]-1]
        a = point[idx1] - point[face]
        b = point[idx2] - point[face]
        la = np.sum(a**2, axis=1)
        lb = np.sum(b**2, axis=1)
        x = np.arccos(np.sum(a*b, axis=1)/np.sqrt(la*lb))
        return np.degrees(x)

    def volume(self):
        pass

    def face_area(self):
        pass

    def face_unit_normal(self):
        pass

    def edge_unit_tagent(self):
        pass

class PolyhedronMeshDataStructure():
    def __init__(self, N, face, faceLocation, face2cell, NC=None):
        self.N = N 
        self.NF = faceLocation.shape[0] - 1
        if NC is None:
            self.NC = np.max(face2cell) + 1
        else:
            self.NC = NC

        self.face = face
        self.faceLocation = faceLocation
        self.face2cell = face2cell

        self.construct()

    def reinit(self, N, face, faceLocation, face2cell, NC=None):
        self.N = N 
        self.NF = faceLocation.shape[0] - 1
        if NC is None:
            self.NC = np.max(face2cell) + 1
        else:
            self.NC = NC

        self.face = face
        self.faceLocation = faceLocation
        self.face2cell
        self.construct()

    def clear(self):
        self.edge = None 
        self.face2edge = None

    def number_of_vertices_of_faces(self):
        faceLocation = self.faceLocation 
        return faceLocation[1:] - faceLocation[0:-1] 

    def number_of_edges_of_faces(self):
        faceLocation = self.faceLocation 
        return faceLocation[1:] - faceLocation[0:-1] 

    def total_edge(self):
        face = self.face
        faceLocation = self.faceLocation

        totalEdge = np.zeros((len(face), 2), dtype=np.int)
        totalEdge[:, 0] = face 
        totalEdge[:-1, 1] = face[1:] 
        totalEdge[faceLocation[1:] - 1, 1] = face[faceLocation[:-1]]

        return totalEdge

    def construct(self):

        totalEdge = self.total_edge()
        _, i0, j = unique_row(np.sort(totalEdge, axis=1))

        self.NE = len(i0) 

        self.edge = totalEdge[i0]
        self.face2edge = j

        return 

    def cell_to_point(self):
        N = self.N
        NF = self.NF
        NC = self.NC

        face = self.face
        face2cell = self.face2cell

        NFV = self.number_of_vertices_of_faces()

        I = np.repeat(face2cell[:, 0], NFV)
        val = np.ones(len(face), dtype=np.bool)
        cell2point = coo_matrix((val, (I, face)), shape=(NC, N), dtype=np.bool)

        I = np.repeat(face2cell[:, 1], NFV)
        cell2point+= coo_matrix((val, (I, face)), shape=(NC, N), dtype=np.bool)

        return cell2point.tocsr()

    def cell_to_edge(self):
        NC = self.NC
        NE = self.NE
        NF = self.NF 

        face = self.face
        face2edge = self.face2edge
        face2cell = self.face2cell

        NFE = self.number_of_edges_of_faces()

        val = np.ones(len(face), dtype=np.bool)
        I = np.repeat(face2cell[:, 0], NFE)
        cell2edge = coo_matrix((val, (I, face2edge)), shape=(NC, NE), dtype=np.bool)

        I = np.repeat(face2cell[:, 1], NFE)
        cell2edge += coo_matrix((val, (II, face2edge)), shape=(NC, NE), dtype=np.bool) 

        return cell2edge.tocsr()

    def cell_to_edge_sign(self):
        pass

    def cell_to_face(self):
        NC = self.NC
        NF = self.NF

        face = self.face
        face2cell = self.face2cell

        val = np.ones((NF,), dtype=np.bool)
        cell2face = coo_matrix((val, (face2cell[:, 0], range(NF))), shape=(NC, NF), dtype=np.bool)
        cell2face+= coo_matrix((val, (face2cell[:, 1], range(NF))), shape=(NC, NF), dtype=np.bool)

        return cell2face.tocsr()

    def cell_to_cell(self):
        NC = self.NC
        face2cell = self.face2cell

        isInFace = (face2cell[:,0] != face2cell[:,1])

        val = np.ones(isInface.sum(), dtype=np.bool)
        cell2cell = coo_matrix((val, (face2cell[isInface, 0], face2cell[isInFace, 1])), shape=(NC, NC), dtype=np.bool)
        cell2cell += coo_matrix((val, (face2cell[isInface, 1], face2cell[isInFace, 0])), shape=(NC, NC), dtype=np.bool)
        return cell2cell.tocsr()

    def face_to_point(self):
        N = self.N
        NF = self.NF

        face = self.face
        NFV = self.number_of_vertices_of_faces()

        I = np.repeat(range(NF), NFV)
        val = np.ones(len(face), dtype=np.bool)
        face2point = csr_matrix((val, (I, face)), shape=(NF, N), dtype=np.bool)
        return face2point

    def face_to_edge(self, sparse=False):
        NF = self.NF
        NE = self.NE
        face2edge = self.face2edge
        if sparse == False:
            return face2edge
        else:
            face = self.face
            NFE = self.number_of_edges_of_faces()
            I = np.repeat(range(NF), NFE)

            val = np.ones(len(face), dtype=np.bool)
            face2edge = csr_matrix((val, (I, face2edge)), shape=(NF, NE), dtype=np.bool)
            return face2edge

    def face_to_face(self):
        pass

    def face_to_cell(self, sparse=False):
        NF = self.NF
        NC = self.NC
        face2cell = self.face2cell
        if sparse == False:
            return face2cell
        else:
            face = self.face
            val = np.ones((NF,), dtype=np.bool)
            face2cell = coo_matrix((val, (range(NF), face2cell[:, 0])), shape=(NF, NC), dtype=np.bool)
            face2cell+= coo_matrix((val, (range(NF), face2cell[:, 1])), shape=(NF, NC), dtype=np.bool)
            return face2cell.tocsr()

    def edge_to_point(self, sparse=False):
        N = self.N
        NE = self.NE
        edge = self.edge
        if sparse == False:
            return edge
        else:
            val = np.ones(NE, dtype=np.bool)
            edge2point = coo_matrix((val, (range(NE), edge[:,0])), shape=(NE, N), dtype=np.bool)
            edge2point+= coo_matrix((val, (range(NE), edge[:,1])), shape=(NE, N), dtype=np.bool)
            return edge2point.tocsr()

    def edge_to_edge(self):
        edge2point = self.edge_to_point()
        return edge2point*edge2point.transpose()

    def edge_to_face(self):
        NE = self.NE
        NF = self.NF

        face = self.face
        face2edge = self.face2edge
        NFE = self.number_of_edges_of_faces()
 
        J = np.repeat(range(NF), NFE) 
        val = np.ones(len(face), dtype=np.bool) 
        edge2face = coo_matrix((val, (face2edge, J)), shape=(NE, NF), dtype=np.bool)
        return edge2face.tocsr()

    def edge_to_cell(self):
        NE = self.NE
        NC = self.NC
        NF = self.NF

        face = self.face
        face2edge = self.face2edge
        face2cell = self.face2cell

        NFE = self.number_of_edges_of_faces()

        J = np.repeat(face2cell[:, 0], NFE)
        val = np.ones(len(face), dtype=np.bool)
        edge2cell = coo_matirx((val, (face2edge, J)), shape=(NE, NC), dtype=np.bool)

        J = np.repeat(face2cell[:, 1], NFE)
        edge2cell += coo_matrix((val, (face2edge, J)), shape=(NE, NC), dtype=np.bool)

        return edge2cell.tocsr()
    
    def point_to_point(self):
        N = self.N
        NE = self.NE
        edge = self.edge
        I = edge.flatten()
        J = edge[:,[1,0]].flatten()
        val = np.ones((2*NE,), dtype=np.bool)
        point2point = csr_matrix((val, (I, J)), shape=(N, N),dtype=np.bool)
        return point2point

    def point_to_edge(self):
        N = self.N
        NE = self.NE
        
        edge = self.edge
        I = edge.flatten()
        J = np.repeat(range(NE), 2)
        val = np.ones(NE, dtype=np.bool)
        point2edge = csr_matrix((val, (I, J)), shape=(N, NE), dtype=np.bool)
        return point2edge

    def point_to_face(self):
        N = self.N
        NF = self.NF

        face = self.face
        NFV = self.number_of_vertices_of_faces()

        J = np.repeat(range(NF), NFV)
        val = np.ones(len(face), dtype=np.bool)
        point2face = csr_matrix((val, (face, J)), shape=(N, NF), dtype=np.bool)
        return point2face


    def point_to_cell(self, cell):
        N = self.N
        NF = self.NF
        NC = self.NC

        face = self.face
        face2cell = self.face2cell
        NFV = self.number_of_vertices_of_faces()

        J = np.repeat(face2cell[:, 0], NFV)
        val = np.ones(len(face), dtype=np.bool)
        point2cell = coo_matrix((val, (face, J)), shape=(N, NC), dtype=np.bool)

        J = np.repeat(face2cell[:, 1], NFV)
        point2cell+= coo_matrix((val, (face, J)), shape=(N, NC), dtype=np.bool)

        return point2cell.tocsr()

    def boundary_point_flag(self):
        N = self.N

        face = self.face

        isBdFace = self.boundary_face_flag() 

        NFV = self.number_of_vertices_of_faces()

        isFaceBdPoint = np.repeat(isBdFace, NFV)

        isBdPoint = np.zeros(N, dtype=np.bool)
        isBdpoint[face[isFaceBdPoint]] = True
        return isBdPoint

    def boundary_edge_flag(self):
        NE = self.NE

        faceLocation = self.faceLocation
        face2edge = self.face2edge

        isBdFace = self.boundary_face_flag()
        NFE = self.number_of_edges_of_faces() 
        isFaceBdEdge = np.repeat(isBdFace, NFE)
        isBdEdge = np.zeros(NE, dtype=np.bool)
        isBdEdge[face2edge[isFaceBdEdge]] = True
        return isBdEdge

    def boundary_face_flag(self):
        face2cell = self.face2cell
        isBdFace = (face2cell[:,0] == face2cell[:,1])
        return isBdFace

    def boundary_cell_flag(self):
        NC = self.NC
        face2cell = self.face2cell
        isBdFace = self.boundary_face_flag()

        isBdCell = np.zeros(NC, dtype=np.bool)
        isBdCell[face2cell[isBdFace, 0]] = True
        return isBdCell

    def boundary_point_index(self):
        isBdPoint = self.boundary_point_flag()
        idx, = np.nonzero(isBdPoint)
        return idx

    def boundary_edge_index(self):
        isBdEdge = self.boundary_edge_flag()
        idx, = np.nonzero(isBdEdge)
        return idx

    def boundary_face_index(self):
        isBdFace = self.boundary_face_flag()
        idx, = np.nonzero(isBdFace)
        return idx

    def boundary_cell_index(self):
        isBdCell = self.boundary_cell_flag()
        idx, = np.nonzero(isBdCell)
        return idx
